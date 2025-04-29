from effis.composition.log import CompositionLogger


class Arguments:

    arguments = []
   

    def __init__(self, value):

        self += value

        
    def __iadd__(self, value):

        if type(value) is type(self):
            self.arguments = self.arguments + value.arguments

        elif (type(value) is not str) and (type(value) is not list):
            print(type(value))
            CompositionLogger.RaiseError(
                ValueError, 
                "Invalid Argument: {0} -- ".format(str(value)) +
                "{0} must be given as a string or a list or strings (or another {0} object)".format(self.__class__.__name__)
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
                        "Invalid Argument: {0} -- ".format(str(value)) +
                        "{0} must be given as a string or a list or strings (or another {0} object)".format(self.__class__.__name__)
                    )

        return self

