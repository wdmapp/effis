import os
from effis.composition.log import CompositionLogger
import effis.composition.arguments as arguments


class Input():
    
    def __init__(self, value, link=False, rename=None, outpath=None):
        if type(value) is not str:
            CompositionLogger.RaiseError(ValueError, "{0} must be given as a string file path".format(self.__name__))
        elif not os.path.exists(value):
            CompositionLogger.RaiseError(FileNotFoundError, "Cannot find input path: {0}".format(value))
        self.inpath = value

        if type(link) is not bool:
            CompositionLogger.RaiseError(ValueError, "link attribute is either True or False")
        self.link = link

        if (rename is not None) and (type(rename) is not str):
            CompositionLogger.RaiseError(ValueError, "rename attribute is given as a string")
        self.rename = rename
        
        if (outpath is not None) and (type(outpath) is not str):
            CompositionLogger.RaiseError(ValueError, "outpath attribute is given as a string")
        self.outpath = outpath


class InputList:

    list = []
    

    def __init__(self, value):
        self.__iadd__(value)
        

    def __iadd__(self, value):
        if isinstance(value, type(self)):
            self.list = self.list + value.list
        if isinstance(value, Input):
            self.list = self.list + [value]
        elif type(value) is str:
            self.list = self.list + [Input(value)]
        elif type(value) is list:
            for item in value:
                self.__iadd__(item)
        else:
            CompositionLogger.RaiseError(ValueError, "{0} can += (string, Input(), lists of these, or another {0} object".format(self.__name__))
            
        return self
