import cmd
from json import loads, dumps, decoder
from traceback import format_exc
from py2r.rDriver import RDriver
from py2r.rUtils import execute_r

class RShell(cmd.Cmd):
    prompt = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cmd = ''
        self.r = RDriver()
        self.r.initiate_libs()

    def emptyline(self):
        cmd = loads(self._cmd)
        self._cmd = ''
        for message in self.r.run(**cmd): 
            print(dumps(message))

    def do_r(self, args):
        message_order = 0
        try:
            for message in self.r.run(**loads(args)):
                if message["type"] != 'log':
                    message["count"] = message_order
                    message_order += 1
                print(dumps(message))
        except:
            print(dumps({"message": f"CLIENT_EXCEPTION (run): unexpected command format {args}: exception: {format_exc()}",
                         "type": "exception",
                         "code": 400}))

    def do_openblankds(self, args):
        try:
            for message in self.r.openblankds(**loads(args)):
                print(dumps(message))
        except decoder.JSONDecodeError:
            print(dumps({"message": f"CLIENT_EXCEPTION (open): unexpected command format {args}",
                         "type": "exception",
                         "code": 400}))
                         
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
    
    def do_refresh(self, args):
        try:
            for message in self.r.refresh(**loads(args)):
                print(dumps(message))
        except decoder.JSONDecodeError:
            print(dumps({"message": f"CLIENT_EXCEPTION (refresh): unexpected command format {args}",
                         "type": "exception",
                         "code": 400}))

    def do_updatemodal(self, args):
        args = loads(args)
        print(dumps({"args":args, "type": "log"}))
        content = execute_r(args["cmd"], eval=True)
        print(dumps({"content":content[0], "type": "log"}))
        print(dumps({"element_id": args["element_id"], "content": content[0], "type": "modalUpdate"}))



if __name__ == '__main__':
    RShell().cmdloop()