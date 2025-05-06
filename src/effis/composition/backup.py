#from effis.composition.input import InputList, Input
from effis.composition.util import InputList, Input
from effis.composition.log import CompositionLogger
import os


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
        super().__init__(value, outpath=outpath, link=False, rename=rename)
        

class Backup:


    def SetSourceEndpoint(self, filename=None):
        if filename is None:
            filename = os.path.join(os.environ["HOME"], ".effis-source-endpoint")
        if not os.path.exists(filename):
            print(
                "The Globus endpoint ID for the current source host has not been set in EFFIS." + "\n",
                "(UUIDs can be search at https://app.globus.org/collections)" + "\n"
                "Please enter it here: ",
                end=""
            )
            endpoint = input().strip()
            with open(filename, "w") as outfile:
                outfile.write(endpoint)
        with open(filename, "r") as infile:
            self.source = infile.read().strip()


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

        self.destinations = {}
        self.source = None
        self.recursive_symlinks = "ignore"

        if value is None:
            self.desinations = {}
        else:
            CompositionLogger.RaiseError(ValueError, "Can only initialize Backup with None")

