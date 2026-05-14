#!/usr/bin/env python3
"""
HTTP-based console for Docker deployment
Provides same functionality as console.py but via HTTP endpoints
"""

import sys
import json
from traceback import format_exc
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from py2r.pylogger import logger

from command_handlers import COMMAND_HANDLERS
from py2r.rDriver import RDriver
from py2r.rUtils import execute_r


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
        logger.info(f'Processing command: {command_type} with args: {args_json}')

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
