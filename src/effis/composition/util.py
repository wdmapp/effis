from effis.composition.log import CompositionLogger, LogKey


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

