import sys
import os
from py2r.pylogger import logger
from trial import check_trial, TrialExpiredError

try:
    logger.info('importing execute_r from rutils and init. R')
    from py2r.rUtils import execute_r
except Exception as e:
    logger.critical("error while importing execute_r")
    raise e

# Set encoding
sys.stdin.reconfigure(encoding='utf-8') if hasattr(sys.stdin, 'reconfigure') else None
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

if __name__ == '__main__':
    try:
        check_trial()
    except TrialExpiredError:
        raise Exception("Trial period expired...")
    else:    
        http_server_port = os.getenv('R_SHELL_HTTP_PORT')
        if http_server_port:
            # start http mode:
            logger.info('Starting in HTTP server mode on port %s', http_server_port)
            from console_http import start_server
            port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
            start_server(port)
        else:
            # start shell mode:
            logger.info('Starting in interactive shell mode')
            from console_shell import RShell
            RShell().cmdloop()
