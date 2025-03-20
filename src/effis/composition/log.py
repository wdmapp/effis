import logging


class CompositionLogger:
    
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('EFFIS [%(asctime)s.%(msecs)03d] - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    #formatter = logging.Formatter('EFFIS: %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S.%03d")

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
