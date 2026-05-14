from cmd import Cmd
from sys import exit
from json import loads, dumps
from traceback import format_exc
from py2r.pylogger import logger
from command_handlers import COMMAND_HANDLERS
from r_shell_base import RShellBase


class RShell(RShellBase, Cmd):
    prompt = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cmd = ''
        for message in self._init_libs():
            print(dumps(message))
        print(dumps(self._get_r_version()))

    def emptyline(self):
        try:
            cmd = loads(self._cmd)
            self._cmd = ''
            for message in self.r.run(**cmd):
                print(dumps(message))
        except:
            logger.error(f"JSON encoding failed for {self._cmd}")

    def default(self, line):
        """Dispatch all commands through the shared COMMAND_HANDLERS registry."""
        cmd, args, _ = self.parseline(line)
        handler = COMMAND_HANDLERS.get(cmd)
        if handler is None:
            print(dumps({"message": f"Unknown command: {cmd}", "type": "exception", "code": 400}))
            return
        try:
            parsed_args = loads(args) if args else {}
            for message in handler.handle(self, parsed_args):
                try:
                    print(dumps(message))
                except TypeError:
                    print(dumps({"message": str(message), "type": "exception"}))
        except Exception:
            print(dumps({
                "message": f"EXCEPTION ({cmd}): {format_exc()}",
                "type": "exception",
                "code": 500
            }))

    def do_quit(self, args):
        print(dumps({"message": "Shutting down python backend", "type": "log"}))
        exit(0)


if __name__ == '__main__':
    RShell().cmdloop()
