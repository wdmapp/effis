import logging
import traceback
import sys


class CompositionLogger:
    
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    #formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S.%03d")
    formatter = logging.Formatter('%(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S.%03d")

    streamhandler = logging.StreamHandler()
    streamhandler.setLevel(logging.WARNING)
    streamhandler.setFormatter(formatter)
    log.addHandler(streamhandler)

    #TracebackLimit = -1


    @classmethod
    def SetLevel(cls, level):
        cls.streamhandler.setLevel(level)


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
    def RaiseError(cls, MyError, msg):
        cls.log.error(msg)
        raise MyError(msg)

        # Could filter traceback stack to hide full trace from user, but it's not clear to me how to properly interact with Jupyter/IPython sessions
        """
        try:
            raise MyError(msg)
        except:            
            stack = traceback.extract_stack()
            print(len(stack))
            traceback.print_stack(stack)
            
            #traceback.print_stack(limit=cls.TracebackLimit)
            #sys.exit(1)
        """
        

