from cmd import Cmd
from sys import exit
from json import loads, dumps
from traceback import format_exc
from py2r.pylogger import logger
from command_handlers import dispatch_command
from r_shell_base import RShellBase
from trial import check_trial, TrialExpiredError

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
            check_trial()
        except TrialExpiredError:
            raise Exception("Trial period expired.")
        try:
            cmd = loads(self._cmd)
            self._cmd = ''
            for message in self.r.run(**cmd):
                print(dumps(message))
        except:
            logger.error(f"JSON encoding failed for {self._cmd}")

    def default(self, line):
        """Dispatch all commands through the shared dispatch_command chokepoint."""
        cmd, args, _ = self.parseline(line)
        try:
            parsed_args = loads(args) if args else {}
            for message in dispatch_command(self, cmd, parsed_args):
                try:
                    print(dumps(message))
                except TypeError:
                    print(dumps({"message": str(message), "type": "exception"}))
        except TrialExpiredError:
            raise Exception("Trial period expired.")
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
    try:
        check_trial()
    except TrialExpiredError:
        raise Exception("Trial period expired.")
    RShell().cmdloop()
