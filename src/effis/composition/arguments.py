from effis.composition.log import CompositionLogger


class Arguments:
    
    def __init__(self, value):
        if type(value) is type(self):
            self.arguments = value.arguments
        elif (type(value) is not str) and (type(value) is not list):
            CompositionLogger.RaiseError(ValueError, "{0} must be given as a string or a list or string (or another {0} object)".format(self.__name__))
        elif type(value) is str:
            self.arguments = [value]
        elif type(value) is list:
            self.arguments = value
        
    def __iadd__(self, value):
        if type(value) is type(self):
            self.arguments = self.arguments + value.arguments
        elif (type(value) is not str) and (type(value) is not list):
            CompositionLogger.RaiseError(ValueError, "{0} must be given as a string or a list or strings (or another {0} object)".format(self.__name__))
        elif type(value) is str:
            self.arguments = self.arguments + [value]
        elif type(value) is list:
            self.arguments = self.arguments + value
        return self

