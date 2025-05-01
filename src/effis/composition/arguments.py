from effis.composition.log import CompositionLogger, LogKey


class Arguments:

    key = "+"
    arguments = []
   

    def __init__(self, value, key="+"):

        with LogKey(self, key):
            self += value

        
    def __iadd__(self, value):

        if type(value) is type(self):
            self.arguments = self.arguments + value.arguments

        elif (type(value) is not str) and (type(value) is not list):
            CompositionLogger.RaiseError(
                ValueError, 
                (
                    "Invalid assignment: {0}={1} --> "
                    "Must be given as a string or a list or strings".format(
                        selflkey,
                        str(value)
                    )
                )
            )

        elif type(value) is str:
            self.arguments = self.arguments + [value]

        elif type(value) is list:
            for v in value:
                if type(v) is str:
                    self += v
                else:
                    CompositionLogger.RaiseError(
                        ValueError, 
                        (
                            "Invalid assignment: {0}={1} --> "
                            "Must be given as a string or a list or strings; "
                            "Element={2} is not a string".format(
                                self.key,
                                str(value),
                                str(v)
                            )
                        )
                    )

        return self

