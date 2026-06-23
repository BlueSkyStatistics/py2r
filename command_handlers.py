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
from typing import Protocol, Iterable, ClassVar, Dict, Type, Any
from traceback import format_exc

from py2r.pyConsole import run_py
from py2r.pylogger import logger
from py2r.rUtils import execute_r, execute_r_complete_list
from r_shell_base import RShellBase


class CommandHandler(Protocol):
    """Protocol for a single ``command_type`` handler.

    Implementations are registered in :data:`COMMAND_HANDLERS` and invoked
    by :meth:`RShellHTTP.process_command`.
    """

    command_type: ClassVar[str]

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
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

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        yield from self._with_order(shell.r.run(**args))


class RHelpCommandHandler:
    """Execute an R help command; messages are returned as-is (no ordering)."""

    command_type: ClassVar[str] = 'rhelp'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        yield from shell.r.run(**args)


class PyCommandHandler(_OrderedMessageMixin):
    """Execute a Python snippet via :func:`run_py`."""

    command_type: ClassVar[str] = 'py'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        yield from self._with_order(run_py(**args))


class MarkdownCommandHandler:
    """Wrap a markdown payload as a single ``markdown`` message."""

    command_type: ClassVar[str] = 'md'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
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


class PasteCellsCommandHandler:
    """Paste cells into the datagrid via the R driver."""

    command_type: ClassVar[str] = 'pastecells'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        logger.info(f"pastecells args: {args}")
        yield from shell.r.paste_datagrid(**args)


class OpenBlankDatasetCommandHandler:
    """Open a blank dataset in the R driver."""

    command_type: ClassVar[str] = 'openblankds'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        yield from shell.r.openblankds(**args)


class OpenCommandHandler:
    """Open a dataset in the R driver."""

    command_type: ClassVar[str] = 'open'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        yield from shell.r.open(**args)


class RefreshCommandHandler:
    """Refresh the currently open dataset."""

    command_type: ClassVar[str] = 'refresh'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        yield from shell.r.refresh(**args)


class GetCellCommandHandler:
    """Retrieve a single cell value from the R driver."""

    command_type: ClassVar[str] = 'getcell'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        yield from shell.r.getcell(**args)


class SearchCommandHandler:
    """Find all cells matching a search term in the dataset (Ctrl+F)."""

    command_type: ClassVar[str] = 'search'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        yield from shell.r.search(**args)


class UpdateModalCommandHandler:
    """Evaluate R code and emit a ``modalUpdate`` message for the client."""

    command_type: ClassVar[str] = 'updatemodal'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        try:
            content = execute_r(args["cmd"], eval=True)
            if content[1] == 'NILSXP':
                content = ""
            else:
                content = content[0]
        except Exception:
            yield {
                "message": f"DATA_EXCEPTION (updatemodal): {format_exc()}\n command: {args['cmd']}",
                "type": "exception",
                "code": 500,
            }
            content = ""
        yield {
            "element_id": args["element_id"],
            "content": content,
            "type": "modalUpdate",
        }


class GetAutocompleteStringsCommandHandler:
    """Return R console autocomplete suggestions."""

    command_type: ClassVar[str] = 'getautocompletestrings'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        logger.info("get_autocomplete_strings")
        try:
            content = execute_r_complete_list(args["cmd"], eval=True, limit=-1)
        except Exception:
            yield {
                "message": f"DATA_EXCEPTION (getautocompletestrings): {format_exc()}\n command: {args['cmd']}",
                "type": "exception",
                "code": 500,
            }
            content = ""
        yield {"element_id": args["element_id"], "content": content, "type": "rconsole_autocomplete"}


class GetPackagesForAutocompleteCommandHandler:
    """Return R package list for autocomplete."""

    command_type: ClassVar[str] = 'getpackagesforautocomplete'

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        logger.info("get_packages_for_autocomplete")
        try:
            content = execute_r_complete_list(args["cmd"], eval=True, limit=-1)
        except Exception:
            yield {
                "message": f"DATA_EXCEPTION (getpackagesforautocomplete): {format_exc()}\n command: {args['cmd']}",
                "type": "exception",
                "code": 500,
            }
            content = ""
        yield {"element_id": args["element_id"], "content": content, "type": "rconsole_packages_autocomplete"}


class CloneCommandHandler:
    """Clone a git repository via :func:`clone_repo`, if git is available."""

    command_type: ClassVar[str] = 'clone'

    def __init__(self):
        try:
            from py2r.git_market import clone_repo
            self.clone_repo = clone_repo
        except Exception as e:
            self.clone_repo = None
            self.exc = str(e)

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
        if self.clone_repo:
            self.clone_repo(args)
            yield {"content": "done", "type": "git_clone"}
        yield {
            "message": "GIT_CONFIG (clone): git was not able to load due to exception on import",
            "type": "exception",
            "code": 500,
        }


class CheckInstalledCommandHandler:
    """Return the set of installed (non-priority) R packages."""

    command_type: ClassVar[str] = 'check_installed'

    _R_SCRIPT: ClassVar[str] = (
        "ip = as.data.frame(installed.packages()[,c(1,3:4)])\n"
        "    ip = ip[is.na(ip$Priority),1:2,drop=FALSE]\n"
        "    ip\n                    "
    )

    def handle(self, shell: 'RShellBase', args: dict) -> Iterable[dict]:
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
    PasteCellsCommandHandler,
    OpenBlankDatasetCommandHandler,
    OpenCommandHandler,
    RefreshCommandHandler,
    GetCellCommandHandler,
    SearchCommandHandler,
    UpdateModalCommandHandler,
    GetAutocompleteStringsCommandHandler,
    GetPackagesForAutocompleteCommandHandler,
    CloneCommandHandler,
    CheckInstalledCommandHandler,
)
