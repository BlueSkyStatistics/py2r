from sys import exit
from json import loads, dumps, decoder
from traceback import format_exc
from py2r.rDriver import RDriver
from py2r.rUtils import execute_r

import asyncio
from rinterface_lib.callbacks import yesnocancel
import websockets
import collections
import threading
from time import sleep
import ctypes
import inspect
import signal
from rpy2.rinterface_lib.embedded import RRuntimeError


def _async_raise(tid, exctype):
    '''Raises an exception in the threads with id tid'''
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid),
                                                     ctypes.py_object(exctype))
    
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # "if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class ThreadWithExc(threading.Thread):
    '''A thread class that supports raising an exception in the thread from
       another thread.
    '''
    def _get_my_tid(self):
        """determines this (self's) thread id

        CAREFUL: this function is executed in the context of the caller
        thread, to get the identity of the thread represented by this
        instance.
        """
        if not self.isAlive():
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        # TODO: in python 2.6, there's a simpler way to do: self.ident

        raise AssertionError("could not determine the thread's id")

    def raiseExc(self, exctype):
        """Raises the given exception type in the context of this thread.

        If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored.

        If you are sure that your exception should terminate the thread,
        one way to ensure that it works is:

            t = ThreadWithExc( ... )
            ...
            t.raiseExc( SomeException )
            while t.isAlive():
                time.sleep( 0.1 )
                t.raiseExc( SomeException )

        If the exception is to be caught by the thread, you need a way to
        check that your thread has caught it.

        CAREFUL: this function is executed in the context of the
        caller thread, to raise an exception in the context of the
        thread represented by this instance.
        """
        _async_raise( self._get_my_tid(), exctype )

r = RDriver()
ws_incomming_queue = collections.deque(maxlen=100) 
ws_outgoing_queue = collections.deque(maxlen=100) 
workers_count = 2
global workers
workers = []
def emptyline(self):
    cmd = loads(self._cmd)
    self._cmd = ''
    for message in self.r.run(**cmd): 
        yield message

def init(args):
    for message in r.initiate_libs():
        yield message
    yield {"message": "initialized", "type": "init_done"}

def rhelp(args):
    r.rhelp(**loads(args))
    yield {"message": "Help done", "type": "log"}

def runR(args):
    message_order = 0
    try:
        for message in r.run(**loads(args)):
            if message["type"] != 'log':
                message["count"] = message_order
                message_order += 1
            try:
                yield message 
            except TypeError:
                yield  {"message": str(message), "type": "exception"} 
    except:
        yield  {"message": f"CLIENT_EXCEPTION (run): unexpected command format {args.encode('utf8')}: exception: {format_exc()}",
                    "type": "exception", "code": 400}

def openblanks(args):
    try:
        for message in r.openblankds(**loads(args)):
            yield message 
    except decoder.JSONDecodeError:
        yield  {"message": f"CLIENT_EXCEPTION (openblank): unexpected command format {args}",
                    "type": "exception", "code": 400}
    except:
        yield {"message": f"CLIENT_EXCEPTION (openblank): unexpected command format {args.encode('utf8')}: exception: {format_exc()}",
                    "type": "exception", "code": 500}

def opendataset(args):
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
        for message in r.open(**loads(args)):
            yield message
    except decoder.JSONDecodeError:
        yield {"message": f"CLIENT_EXCEPTION (open): unexpected command format {args}",
                    "type": "exception", "code": 400}
    except Exception:
        yield {"message": f"DATA_EXCEPTION (open): {format_exc()}",
                    "type": "exception", "code": 500}

def refresh(args):
    try:
        for message in r.refresh(**loads(args)):
            yield message
    except decoder.JSONDecodeError:
        yield {"message": f"CLIENT_EXCEPTION (refresh): unexpected command format {args}",
                    "type": "exception", "code": 400}
    except Exception:
        yield {"message": f"DATA_EXCEPTION (refresh): {format_exc()}",
                    "type": "exception", "code": 500}

def quit(args):
    yield {"message": "Shitting down python backend", "type": "halt"}

def updatemodal(args):
    args = loads(args)
    content = execute_r(args["cmd"], eval=True)
    yield {"element_id": args["element_id"], "content": content[0], "type": "modalUpdate"}

async def handle_message(message):
    print(f"imcomming: {message}")
    if message == 'abort':
        global workers
        for worker in workers:
            worker.raiseExc( OSError )
            try:
                while worker.isAlive():
                    await asyncio.sleep( 1 )
                    worker.raiseExc( OSError )
            except RuntimeError:
                pass
            print("worker dead")
            worker.join()
        create_workers()
        print(len(workers))
    else:
        ws_incomming_queue.appendleft(message)
    
def producer(message):
    commands = {
        'init': init,
        'rhelp': rhelp,
        'r': runR,
        'openblankds': openblanks,
        'open': opendataset,
        'refresh': refresh,
        'quit': quit,
        'updatemodal': updatemodal
    }
    cmd = message.split(" ", 1)
    if cmd[0] in commands.keys():
        for message in commands[cmd[0]](None if len(cmd) == 1 else cmd[1]):
             yield(message)

async def consumer_handler(websocket, path):
    async for message in websocket:
        await handle_message(message)

def worker_handler():
    while True:
        if len(ws_incomming_queue) > 0 :
            message = ws_incomming_queue.pop()
            print(f"processing: {message}")
            for resp in producer(message):
                ws_outgoing_queue.appendleft(resp)
            if message in ["quit", "abort"]:
                break
        sleep(0.1)   

async def producer_handler(websocket, path):
    while True:
        if len(ws_outgoing_queue) > 0 :
            message = ws_outgoing_queue.pop()
            await websocket.send(dumps(message, ensure_ascii=False))  
            if 'type' in message and message['type'] == 'halt':
                for _ in range(workers_count):
                    ws_incomming_queue.appendleft("quit")
                for worker in workers:
                    worker.join()
                exit(0)
        else:
            await asyncio.sleep(0.1)

async def rshell(websocket, path):
    consumer_task = asyncio.ensure_future(
        consumer_handler(websocket, path))
    producer_task = asyncio.ensure_future(
        producer_handler(websocket, path))
    done, pending = await asyncio.wait(
        [consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()

def create_workers():
    global workers
    workers = []
    for _ in range(workers_count):
        workers.append(ThreadWithExc(target=worker_handler))
        workers[-1].start()

if __name__ == '__main__':
    wss = websockets.serve(rshell, "localhost", 8765)
    create_workers()
    asyncio.get_event_loop().run_until_complete(wss)
    asyncio.get_event_loop().run_forever()
