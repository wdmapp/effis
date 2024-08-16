from effis.composition.input import InputList
from effis.composition.input import Input
from effis.composition.log import CompositionLogger


class Destination:

    def __init__(self, endpoint):
        self.Endpoint = endpoint
        #self.Input = effis.composition.input.InputList([])
        self.Input = InputList([])


    def __iadd__(self, value):
        self.Input += value
        return self.Input


class SendData(Input):
    
    def __init__(self, value, outpath=None, rename=None):
        if outpath is None:
            CompositionLogger.RaiseError(ValueError, "Need to give an outpath for Backup SendData")
        super(SendData, self).__init__(value, outpath=outpath, link=False, rename=rename)
        

class Backup:

    destinations = {}
    source = None


    def __getitem__(self, key):
        return self.destinations[key]


    def __setitem__(self, key, item):

        if type(item) is Destination:
            self.destinations[key] = item

        #elif type(item) is effis.composition.input.InputList:
        elif type(item) is InputList:
            self.destinations[key].Input = item

        else:
            CompositionLogger.RaiseError(ValueError, "Bad value for Backup: key={0}, value={1}".format(key, item))



    def __init__(self, value=None):

        if value is None:
            self.desinations = {}
        else:
            CompositionLogger.RaiseError(ValueError, "Can only initialize Backup with None")

