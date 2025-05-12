import logging
import shutil
from contextlib import ContextDecorator

import sys
import traceback
from colorama import Fore, Back, Style


class LogKey(ContextDecorator):

    def __init__(self, thing, key):

        if (type(key) is not str):
            CompositionLogger.RaiseError(
                ValueError, 
                "LogKey must be given as a string -- gave {0}".format(key)
            )

        if "key" in dir(thing):
            self.haskey = True
            self.oldkey = thing.key
        else:
            self.haskey = False

        self.newkey = key
        self.thing = thing


    def __enter__(self):
        self.thing.key = self.newkey
        return self


    def __exit__(self, *exc):
        if self.haskey:
            self.thing.key = self.oldkey
        else:
            del self.thing.key

        return None


class EffisFormatter(logging.Formatter):

    FORMATS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Style.BRIGHT + Fore.RED,
    }


    def __init__(
        self,
        fmt='EFFIS [%(asctime)s.%(msecs)03d]  %(levelname)-8s  %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S"
    ):
        logging.Formatter.__init__(self, fmt=fmt, datefmt=datefmt)

        self.last = None
        self.cols, self.lines = shutil.get_terminal_size(fallback=(150,10))

        self.startsize = (
            5 +             # EFFIS
            1 + 2 + 2 +     # Explicit Spaces
            2 +             # Brackets
            10 + 1 + 12 +   # Date, Space, Time (what's in the brackets)
            8               # levelname field
        )


    def format(self, record):
        format_orig = self._fmt

        comp = self.cols - self.startsize - len(record.msg)

        if (comp < 0) or (record.msg.endswith("\n")):
            if self.last != "long":
                self._fmt = "\n" + self._fmt + "\n"
            else:
                self._fmt = self._fmt + "\n"

            if record.msg.endswith("\n"):
                self._fmt = self._fmt.rstrip("\n")

            self.last = "long"
        else:
            self.last = "short"

        if shutil.get_terminal_size(fallback=(-1, -1)) != (-1, -1):
            self._fmt = self.FORMATS.get(record.levelno) + self._fmt + Style.RESET_ALL

        self._style = logging.PercentStyle(self._fmt)
        result = logging.Formatter.format(self, record)
        self._fmt = format_orig
        return result


class CompositionLogger:
    ERROR = False
    
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    #formatter = logging.Formatter('EFFIS [%(asctime)s.%(msecs)03d] - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    formatter = EffisFormatter()

    streamhandler = logging.StreamHandler()
    #streamhandler.setLevel(logging.WARNING)
    streamhandler.setLevel(logging.INFO)
    streamhandler.setFormatter(formatter)
    log.addHandler(streamhandler)


    @classmethod
    def SetLevel(cls, level):
        cls.streamhandler.setLevel(level)

    @classmethod
    def SetWarning(cls):
        cls.streamhandler.setLevel(logging.WARNING)

    @classmethod
    def SetDebug(cls):
        cls.streamhandler.setLevel(logging.DEBUG)

    @classmethod
    def Info(cls, msg):
        cls.log.info(msg)

    @classmethod
    def Warning(cls, msg):
        cls.log.warning(msg)
        
    @classmethod
    def Debug(cls, msg):
        cls.log.debug(msg)
        
        
    @classmethod
    def RunnerError(cls, msg):
        return cls.RaiseError(ValueError, msg)


    @classmethod
    def RaiseError(cls, MyError, msg):

        cls.ERROR = True
        cls.log.error(msg + "\n")

        '''
        stack = traceback.extract_stack(limit=-2)
        stack = ''.join(traceback.format_list(stack))
        cls.log.error(msg + "\n" + stack.strip() )
        '''

        #raise SystemExit(msg)
        #sys.tracebacklimit = 0
        raise MyError(msg)

