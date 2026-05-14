import cmd
from sys import exit
from json import loads, dumps
from traceback import format_exc
from py2r.pylogger import logger
from command_handlers import COMMAND_HANDLERS
from r_shell_base import RShellBase

try:
    logger.info('importing execute_r from rutils and init. R')
    from py2r.rUtils import execute_r
except Exception as e:
    logger.critical("error while importing execute_r")
    raise e

from py2r.rDriver import RDriver

class RShell(RShellBase, cmd.Cmd):
    prompt = ''

    def __init__(self, *args, **kwargs):
        # start = time()
        super().__init__(*args, **kwargs)
        self._cmd = ''
        self.r = RDriver()
        # print(dumps({"message": f"RDriver initialized: {int(time()-start)}", "type": "log"}))
        # start = time()
        for message in self.r.initiate_libs():
            print(dumps(message))
        # print(dumps({"message": f"Libs initialized: {int(time()-start)}", "type": "log"}))
        print(dumps({"message": "initialized", "type": "init_done"}))
        rversioncmd = "RMajorMinorver =list(major = R.version$major, minor = R.version$minor)"
        execute_r(rversioncmd)
        rc, _ = execute_r("jsonlite::toJSON(RMajorMinorver, na = NULL)")
        r_version = loads(rc[0])
        print(dumps({"message": r_version, "type": "rversion"}))

    def emptyline(self):
        try:
            cmd = loads(self._cmd)
            self._cmd = ''
            for message in self.r.run(**cmd):
                print(dumps(message))
        except:
            print(f"JSON encoding failed for {self._cmd}")

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
