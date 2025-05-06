from effis.composition.log import CompositionLogger, LogKey
import os


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


class ListType:

    key = "+"
    List = []


    class AssignmentError(Exception):
        pass


    def ErrorMessage(self, given, element=None):
        if element is None:
            element = given
        return (
            "Invalid assignment: {0}={1} --> "
            "Must be given as {2} object or list of {2} objects; "
            "{3} is not.".format(
                self.key,
                str(given),
                self.astype.__name__,
                str(element)
            )
        )


    def __iter__(self):
        self.index = 0
        return self


    def __next__(self):
        if self.index == len(self.List):
            raise StopIteration
        self.index = self.index + 1
        return self.List[self.index - 1]


    def __len__(self):
        return len(self.List)

    
    def __getitem__(self, selection):
        return self.List[selection]


    def __init__(self, value, astype, key="+"):

        self.astype = astype

        with LogKey(self, key):
            self += value



    def __iadd__(self, value):

        if type(value) is type(self):
            self.List = self.List + value.List

        elif (not isinstance(value, self.astype)) and (not isinstance(value, list)):
            CompositionLogger.RaiseError(
                self.AssignmentError, 
                self.ErrorMessage(value)
            )

        elif isinstance(value, list):
            for v in value:
                if isinstance(v, self.astype):
                    self += v
                else:
                    CompositionLogger.RaiseError(
                        self.AssignmentError, 
                        self.ErrorMessage(value, element=v)
                    )

        elif isinstance(value, self.astype):
            self.List = self.List + [value]

        return self


class Arguments(ListType):

    def __init__(self, value, key="+"):
        super().__init__(value, str, key=key)
        self.arguments = self.List


class InputList(ListType):

    def __init__(self, value, key="+"):
        super().__init__(value, Input, key=key)
        self.list = self.List


    def __iadd__(self, value):

        if isinstance(value, str):
            value = Input(value, key=self.key)

        return super().__iadd__(value)


