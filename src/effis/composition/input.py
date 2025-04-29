import os
from effis.composition.log import CompositionLogger


class Input():
    
    def __init__(self, value, link=False, rename=None, outpath=None):

        if type(value) is not str:
            CompositionLogger.RaiseError(
                ValueError, 
                "Invalid Input: {0} -- ".format(str(value)) + 
                "{0} must be given as a string file path".format(self.__class__.__name__)
            )

        elif not os.path.exists(value):
            CompositionLogger.RaiseError(FileNotFoundError, "Cannot find Input path: {0}".format(value))

        elif type(link) is not bool:
            CompositionLogger.RaiseError(ValueError, "link attribute of Input is set as either True or False -- gave {0}".format(str(value)))

        elif (rename is not None) and (type(rename) is not str):
            CompositionLogger.RaiseError(ValueError, "rename attribute of Input is set as a string -- gave {0}".format(str(value)))

        elif (outpath is not None) and (type(outpath) is not str):
            CompositionLogger.RaiseError(ValueError, "outpath attribute of Input is set as a string -- gave {0}".format(str(value)))

        self.inpath = value
        self.link = link
        self.rename = rename
        self.outpath = outpath


class InputError(Exception):
    pass


class InputList:

    list = []
    

    def __init__(self, value):

        self += value
        

    def __iadd__(self, value):

        if isinstance(value, type(self)):
            self.list = self.list + value.list

        elif isinstance(value, Input):
            self.list = self.list + [value]

        elif type(value) is str:
            self.list = self.list + [Input(value)]

        elif type(value) is list:
            for item in value:
                self += item

        else:
            CompositionLogger.RaiseError(
                InputError, 
                "Invalid Input list: {0} -- ".format(str(value)) +
                "Can += string, Input(), lists of these, or another {0} object".format(self.__class__.__name__)
            )
            
        return self

