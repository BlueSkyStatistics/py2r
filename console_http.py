#!/usr/bin/env python3
"""
HTTP-based console for Docker deployment
Provides same functionality as console.py but via HTTP endpoints
"""

import cmd
import sys
import json
from traceback import format_exc
from threading import Thread
import signal
import atexit
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging
from typing import Protocol, Iterable, ClassVar, Dict, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# from py2r.pylogger import logger

# Set encoding
sys.stdin.reconfigure(encoding='utf-8') if hasattr(sys.stdin, 'reconfigure') else None
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Use local R via rpy2 (as original behavior inside the container)
try:
    logger.info('importing execute_r from rutils and init. R')
    from py2r.rUtils import execute_r
except Exception as e:
    logger.critical("error while importing execute_r")
    raise e

from py2r.pyConsole import run_py
from py2r.rDriver import RDriver

try:
    from py2r.git_market import clone_repo

    nogit = False
except:
    nogit = True


# ---------------------------------------------------------------------------
# Command handlers
#
# Each wire ``command_type`` is implemented as a subclass of the
# :class:`CommandHandler` protocol. Handlers are stateless objects that
# receive the active :class:`RShellHTTP` instance (for access to the R
# driver and cached initialization messages) together with the already
# parsed JSON arguments, and yield one or more result messages.
#
# Adding a new command is as simple as declaring a new subclass with a
# ``command_type`` class attribute and implementing :meth:`handle` -- the
# registry at the bottom of this section will pick it up automatically.
# ---------------------------------------------------------------------------


class CommandHandler(Protocol):
    """Protocol for a single ``command_type`` handler.

    Implementations are registered in :data:`COMMAND_HANDLERS` and invoked
    by :meth:`RShellHTTP.process_command`.
    """

    command_type: ClassVar[str]

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        """Yield result messages for the given parsed ``args``."""
        ...


class _OrderedMessageMixin:
    """Helper that tags non-log messages with a monotonically increasing ``count``."""

    @staticmethod
    def _with_order(messages: Iterable[dict]) -> Iterable[dict]:
        message_order = 0
        for message in messages:
            if message["type"] != 'log':
                message["count"] = message_order
                message_order += 1
            yield message


class RCommandHandler(_OrderedMessageMixin):
    """Execute R code through the shared :class:`RDriver`."""

    command_type: ClassVar[str] = 'r'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        yield from self._with_order(shell.r.run(**args))


class RHelpCommandHandler:
    """Execute an R help command; messages are returned as-is (no ordering)."""

    command_type: ClassVar[str] = 'rhelp'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        yield from shell.r.run(**args)


class PyCommandHandler(_OrderedMessageMixin):
    """Execute a Python snippet via :func:`run_py`."""

    command_type: ClassVar[str] = 'py'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        yield from self._with_order(run_py(**args))


class MarkdownCommandHandler:
    """Wrap a markdown payload as a single ``markdown`` message."""

    command_type: ClassVar[str] = 'md'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        yield {
            "message": str(args['cmd']),
            "caption": "",
            "type": "markdown",
            "code": 200,
            "updateDataSet": False,
            "name": args.get('datasetName', None),
            "cmd": args['cmd'],
            "eval": True,
            "parent_id": args.get('parent_id', None),
            "output_id": args.get('output_id', None),
        }


class OpenBlankDatasetCommandHandler:
    """Open a blank dataset in the R driver."""

    command_type: ClassVar[str] = 'openblankds'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        yield from shell.r.openblankds(**args)


class OpenCommandHandler:
    """Open a dataset in the R driver."""

    command_type: ClassVar[str] = 'open'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        yield from shell.r.open(**args)


class RefreshCommandHandler:
    """Refresh the currently open dataset."""

    command_type: ClassVar[str] = 'refresh'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        yield from shell.r.refresh(**args)


class UpdateModalCommandHandler:
    """Evaluate R code and emit a ``modalUpdate`` message for the client."""

    command_type: ClassVar[str] = 'updatemodal'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        content = execute_r(args["cmd"], eval=True)
        if content[1] == 'NILSXP':
            content = ""
        else:
            content = content[0]
        yield {
            "element_id": args["element_id"],
            "content": content,
            "type": "modalUpdate",
        }


class CloneCommandHandler:
    """Clone a git repository via :func:`clone_repo`, if git is available."""

    command_type: ClassVar[str] = 'clone'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        if nogit:
            yield {
                "message": "git was not able to load due to exception on import",
                "type": "exception",
                "code": 500,
            }
            return
        clone_repo(args)
        yield {"content": "done", "type": "git_clone"}


class CheckInstalledCommandHandler:
    """Return the set of installed (non-priority) R packages."""

    command_type: ClassVar[str] = 'check_installed'

    _R_SCRIPT: ClassVar[str] = (
        "ip = as.data.frame(installed.packages()[,c(1,3:4)])\n"
        "    ip = ip[is.na(ip$Priority),1:2,drop=FALSE]\n"
        "    ip\n                    "
    )

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        result: dict = {}
        try:
            content = execute_r(self._R_SCRIPT, eval=True, limit=-1)
            if content[1] != 'NILSXP':
                rows = content[0]
                for record in rows[1:]:
                    result[record[0]] = record[1]
        except Exception:
            pass
        yield {"content": result, "type": "installedPackages"}


class InitCommandHandler:
    """Replay the cached initialization messages collected at startup."""

    command_type: ClassVar[str] = 'init'

    def handle(self, shell: "RShellHTTP", args: dict) -> Iterable[dict]:
        yield from shell.init_messages


def _build_handler_registry(
    *handler_classes: Type[CommandHandler],
) -> Dict[str, CommandHandler]:
    """Instantiate the given handler classes and key them by ``command_type``."""
    registry: Dict[str, CommandHandler] = {}
    for handler_cls in handler_classes:
        cmd_type = handler_cls.command_type
        if cmd_type in registry:
            raise ValueError(
                f"Duplicate command handler registration for {cmd_type!r}"
            )
        registry[cmd_type] = handler_cls()
    return registry


COMMAND_HANDLERS: Dict[str, CommandHandler] = _build_handler_registry(
    RCommandHandler,
    RHelpCommandHandler,
    PyCommandHandler,
    MarkdownCommandHandler,
    OpenBlankDatasetCommandHandler,
    OpenCommandHandler,
    RefreshCommandHandler,
    UpdateModalCommandHandler,
    CloneCommandHandler,
    CheckInstalledCommandHandler,
    InitCommandHandler,
)


class RShellHTTP:
    """HTTP-compatible version of RShell"""

    def __init__(self):
        logger.info("Initializing RShellHTTP...")
        self.r = RDriver()

        # Initialize libs and get R version
        self.init_messages = []
        for message in self.r.initiate_libs():
            self.init_messages.append(message)

        self.init_messages.append({"message": "initialized", "type": "init_done"})

        # Get R version
        rversioncmd = "RMajorMinorver =list(major = R.version$major, minor = R.version$minor)"
        execute_r(rversioncmd)
        rc, _ = execute_r("jsonlite::toJSON(RMajorMinorver, na = NULL)")
        r_version = json.loads(rc[0])
        self.init_messages.append({"message": r_version, "type": "rversion"})

        logger.info("RShellHTTP initialized successfully")

    def process_command(self, command_type, args_json):
        """Process a command and return results by dispatching to a handler."""
        print(f'Processing command: {command_type} with args: {args_json}')

        try:
            args = json.loads(args_json) if args_json else {}

            handler = COMMAND_HANDLERS.get(command_type)
            if handler is None:
                return [{
                    "message": f"Unknown command type: {command_type}",
                    "type": "exception",
                    "code": 400,
                }]

            return list(handler.handle(self, args))

        except Exception as e:
            return [{
                "message": (
                    f"Command execution error: {str(e)}\n"
                    f"{command_type=}\n{args_json=}\n\n{format_exc()}"
                ),
                "format_exc": format_exc(),
                "command_type": command_type,
                "args_json": args_json,
                "type": "exception",
                "code": 500,
            }]


# Global RShell instance
r_shell = None


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests for command execution"""
        try:
            # Parse URL
            parsed_path = urlparse(self.path)
            path = parsed_path.path

            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            if path.startswith('/cmd/'):
                # Extract command type from URL
                command_type = path[5:]  # Remove '/cmd/' prefix

                # Process command
                results = r_shell.process_command(command_type, post_data.decode('utf-8'))

                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                # Send each result as a separate line (to match original console.py behavior)
                for result in results:
                    response_line = json.dumps(result) + '\n'
                    self.wfile.write(response_line.encode('utf-8'))

            else:
                self.send_error(404)

        except Exception as e:
            logger.error(f"Request handling error: {e}")
            self.send_error(500)

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        elif self.path == '/init':
            # Return initialization data
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            for message in r_shell.init_messages:
                response_line = json.dumps(message) + '\n'
                self.wfile.write(response_line.encode('utf-8'))
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        """Custom log message to use Python logging"""
        logger.info("%s - - [%s] %s\n" %
                    (self.address_string(),
                     self.log_date_time_string(),
                     format % args))


def start_server(port=8000):
    """Start the HTTP server"""
    global r_shell

    logger.info("Starting HTTP server...")
    r_shell = RShellHTTP()

    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    logger.info(f"Server started on port {port}")

    def shutdown_handler(signum, frame):
        logger.info("Shutting down server...")
        server.shutdown()
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    finally:
        server.shutdown()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    start_server(port)
