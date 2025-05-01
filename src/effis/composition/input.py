import os
from effis.composition.log import CompositionLogger, LogKey


class Input:

    def __init__(self, value, link=False, rename=None, outpath=None, key=""):

        if type(value) is not str:
            CompositionLogger.RaiseError(
                ValueError, 
                "Invalid Input {0}={1} --> Must be a string (path)".format(key, str(value))
            )

        elif not os.path.exists(value):
            CompositionLogger.RaiseError(
                FileNotFoundError,
                "Invalid file path: Cannot find Input path {0}={1}".format(key, value)
            )

        elif type(link) is not bool:
            CompositionLogger.RaiseError(
                ValueError, 
                "Invalid assignment: link attribute of Input is set as either True or False -- gave {0}".format(str(link))
            )

        elif (rename is not None) and (type(rename) is not str):
            CompositionLogger.RaiseError(
                ValueError, 
                "Invalid assignment: rename attribute of Input is set as a string -- gave {0}".format(str(rename))
            )

        elif (outpath is not None) and (type(outpath) is not str):
            CompositionLogger.RaiseError(
                ValueError, 
                "Invalid assignment: outpath attribute of Input is set as a string -- gave {0}".format(str(outpath))
            )

        self.inpath = value
        self.link = link
        self.rename = rename
        self.outpath = outpath


class InputError(Exception):
    pass


class InputList:

    key = "+"
    list = []
    

    def __init__(self, value, key="+"):

        with LogKey(self, key):
            self += value
        

    def __iadd__(self, value):

        if isinstance(value, type(self)):
            self.list = self.list + value.list

        elif isinstance(value, Input):
            self.list = self.list + [value]

        elif type(value) is str:
            self.list = self.list + [Input(value, key=self.key)]

        elif type(value) is list:
            for item in value:
                if isinstance(value, (Input, str)):
                    self += item
                else:
                    ValueError, 
                    (
                        "Invalid assignment: {0}={1} --> "
                        "Must be given as string, Input(), or list of these; "
                        "Element={2} is not a string or Input instance".format(
                            self.key,
                            str(value),
                            item
                        )
                    )

        else:
            CompositionLogger.RaiseError(
                ValueError, 
                (
                    "Invalid assignment: {0}={1} --> "
                    "Must be given as string, Input(), or list of these".format(
                        self.key,
                        str(value)
                    )
                )
            )
            
        return self

