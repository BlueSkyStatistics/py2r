import cmd
from sys import exit
from json import loads, dumps, decoder
from traceback import format_exc
from py2r.rDriver import RDriver
from py2r.rUtils import execute_r
try:
    #
    # Release 10.2 features
    #
    from py2r.git_market import clone_repo
    from py2r.pyConsole import run_py
    nogit = False
except:
    nogit = True


class RShell(cmd.Cmd):
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

    def emptyline(self):
        try:
            cmd = loads(self._cmd)
            self._cmd = ''
            for message in self.r.run(**cmd):
                print(dumps(message))
        except:
            print(f"JSON encoding failed for {self._cmd}")

    
    def do_rhelp(self, args):
        try:
            for message in self.r.run(**loads(args)):
                print(dumps(message))
        except:
            print(dumps({
                    "message": "R Environment error",
                    "error": format_exc().split('.RRuntimeError:')[1].strip(),
                    "type": "error_dialog"
                }))

    def do_r(self, args):
        message_order = 0
        try:
            for message in self.r.run(**loads(args)):
                if message["type"] != 'log':
                    message["count"] = message_order
                    message_order += 1
                try:
                    print(dumps(message))
                except TypeError:
                    print(dumps({"message": str(message), "type": "exception"}))
        except:
            print(dumps({"message": f"CLIENT_EXCEPTION (run): unexpected command format {args.encode('utf8')}: exception: {format_exc()}",
                         "type": "exception",
                         "code": 400}))

    def do_py(self, args):
        message_order = 0
        try:
            for message in run_py(**loads(args)):
                if message["type"] != 'log':
                    message["count"] = message_order
                    message_order += 1
                try:
                    print(dumps(message))
                except TypeError:
                    print(dumps({"message": str(message), "type": "exception"}))
        except:
            print(dumps({
                            "message": f"CLIENT_EXCEPTION (runpy): unexpected command format {args.encode('utf8')}: exception: {format_exc()}",
                            "type": "exception",
                            "code": 400}))


    def do_openblankds(self, args):
        # start = time()
        try:
            for message in self.r.openblankds(**loads(args)):
                print(dumps(message))
            # print(dumps({"message": f"Blank Dataset open: {int(time()-start)}", "type": "log"}))
        except decoder.JSONDecodeError:
            print(dumps({"message": f"CLIENT_EXCEPTION (openblank): unexpected command format {args}",
                         "type": "exception",
                         "code": 400}))
        except:
            print(dumps({"message": f"CLIENT_EXCEPTION (openblank): unexpected command format {args.encode('utf8')}: exception: {format_exc()}",
                         "type": "exception",
                         "code": 500}))
                         
    def do_open(self, args):
        """
        Args structure is dict with keys:
            file_path,             ## this is filename. use forward slash in path 'C:/bla/bla/file.rdata'
            wsName=NULL,           ## applies to Excel file only. Provide the sheetname
            replace_ds=FALSE,      ## flag to replace already loaded dataset that has the same name.
            csvHeader=TRUE,        ## if first row is header row(column names) or not
            char_to_factor=FALSE,  ## automatically convert character columns to factor
            basket_data=FALSE,     ## this applies to market basket analysis because the data file for that is different
            csv_sep=',',           ## for CSV files. Which character is used as a separator in CSV (or txt) files
            delim='.',             ## I think fo CSV, which character is used for decimal in the data (eg. 123.4 OR 123,4)
            datasetName            ## this is the memory object name for the dataset (user friendly name). 'Dataset1', 'titanic'. in
        """
        try:
            for message in self.r.open(**loads(args)):
                print(dumps(message))
        except decoder.JSONDecodeError:
            print(dumps({"message": f"CLIENT_EXCEPTION (open): unexpected command format {args}",
                         "type": "exception",
                         "code": 400}))
        except Exception:
            print(dumps({"message": f"DATA_EXCEPTION (open): {format_exc()}",
                         "type": "exception",
                         "code": 500}))

    
    def do_refresh(self, args):
        try:
            # start=time()
            for message in self.r.refresh(**loads(args)):
                print(dumps(message))
            # print(dumps({"message": f"Blank Dataset reloaded: {int(time()-start)}", "type": "log"}))
        except decoder.JSONDecodeError:
            print(dumps({"message": f"CLIENT_EXCEPTION (refresh): unexpected command format {args}",
                         "type": "exception",
                         "code": 400}))
        except Exception:
            print(dumps({"message": f"DATA_EXCEPTION (refresh): {format_exc()}",
                         "type": "exception",
                         "code": 500}))

    def do_quit(self, args):
        print(dumps({"message": "Shitting down python backend", "type": "log"}))
        exit(0)

    def do_updatemodal(self, args):
        args = loads(args)
        try:
            content = execute_r(args["cmd"], eval=True)
            if content[1] == 'NILSXP':
                content = ""
            else:
                content = content[0]
        except Exception:
            print(dumps({"message": f"DATA_EXCEPTION (do_updatemodal): {format_exc()}\n command: {args['cmd']}",
                         "type": "exception",
                         "code": 500}))
            content = ""
        print(dumps({"element_id": args["element_id"], "content": content, "type": "modalUpdate"}))

    def do_clone(self, args):
        if nogit:
            return print(dumps({"message": f"GIT_CONFIG (do_clone): git was not able to load "
                                           f"due to exception on import",
                                "type": "exception", "code": 500}))
        args = loads(args)
        try:
            clone_repo(args)
            print(dumps({"content": "done", "type": "git_clone"}))
        except Exception:
            print(dumps({"message": f"GIT_EXCEPTION (do_clone): {format_exc()}\n command: {args}",
                         "type": "exception",
                         "code": 500}))

    def do_check_installed(self, args):
        try:
            cmd = """ip = as.data.frame(installed.packages()[,c(1,3:4)])
    ip = ip[is.na(ip$Priority),1:2,drop=FALSE]
    ip
            """
            content = execute_r(cmd, eval=True, limit=-1)
            if content[1] == 'NILSXP':
                content = ""
            else:
                content = content[0]
        except:
            content = []
        print(dumps({"content": content, "type": "installedPackages"}))


if __name__ == '__main__':
    RShell().cmdloop()
