import logging
import shutil


class EffisFormatter(logging.Formatter):

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

        if comp < 0:
            if self.last != "long":
                self._fmt = "\n" + self._fmt + "\n"
            else:
                self._fmt = self._fmt + "\n"
            self.last = "long"
        else:
            self.last = "short"

        self._style = logging.PercentStyle(self._fmt)
        result = logging.Formatter.format(self, record)
        self._fmt = format_orig
        return result


class CompositionLogger:
    
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    #formatter = logging.Formatter('EFFIS [%(asctime)s.%(msecs)03d] - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    #formatter = logging.Formatter('EFFIS [%(asctime)s.%(msecs)03d]  %(levelname)-8s  %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
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
        cls.log.error(msg)
        raise MyError(msg)
