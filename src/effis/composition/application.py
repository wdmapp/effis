import effis.composition.arguments
import effis.composition.input
from effis.composition.log import CompositionLogger


class Application:

    Name = None
    Filepath = None

    MPIRunnerArguments = []
    CommandLineArguments = []
    
    SetupFile = None
    Environment = {}
    
    Ranks = 1
    RanksPerNode = None
    CoresPerRank = None
    GPUsPerRank = None
    RanksPerGPU = None

    ShareKey = None

    Input = []

    
    def GPUvsRank(self):
        gpunum = None
        ranknum = None
        if (self.GPUsPerRank is not None) and (type(self.GPUsPerRank) is int):
            gpunum = self.GPUsPerRank
            ranknum = 1
        elif (self.GPUsPerRank is not None) and (type(self.GPUsPerRank) is str):
            gpunum, ranknum = self.GPUsPerRank.split(":")
            gpunum = int(gpunum)
            ranknum = int(ranknum)
        elif (self.RanksPerGPU is not None) and (type(self.RanksPerGPU) is int):
            ranknum = app.RanksPerGPU
            gpunum = 1
        elif (self.RanksPerGPU is not None) and (type(self.RanksPerGPU) is str):
            ranknum, gpunum = app.RanksPerGPU.split(":")
            ranknum = int(ranknum.strip())
            gpunum = int(gpunum.strip())
        return gpunum, ranknum
    

    @classmethod
    def CheckApplications(cls, other):
        if type(other) is list:
            for i in range(len(other)):
                if type(other[i]) is not type(cls):
                    CompositionLogger.RaiseError(ValueError, "List elements to add as applications must be of type effis.composition.Application")
        elif type(other) is not type(cls):
            CompositionLogger.RaiseError(ValueError, "Can only add applications and/or lists of them with elements of type effis.composition.Application")
        return other


    # Basic check against Rank settings that don't make sense
    def CheckSensible(self):
        if self.Ranks < 1:
            CompositionLogger.RaiseError(ValueError, "For {0}, cannot set Ranks < 1".format(self.Name))
        if (self.Ranks == 1) and (self.RanksPerNode is None):
            self.RanksPerNode = 1
            CompositionLogger.Info("For {0}, setting RanksPerNode = 1 since Ranks = 1".format(self.Name))
        if (self.Ranks == 1) and (self.RanksPerNode > 1):
            CompositionLogger.RaiseError(ValueError, "For {0}, with Ranks = 1, RanksPerNode must also be 1".format(self.Name))
        if (self.Ranks > 1) and (self.RanksPerNode == None):
            CompositionLogger.RaiseError(AttributeError, "For {0}, with Ranks > 1, please set RanksPerNode".format(self.Name))

        if (self.CoresPerRank is None) and (self.ShareKey is not None):
            CompositionLogger.RaiseError(ValueError, "With node sharing ('{0}'), please set each application's CoresPerRank – Application '{1}' missing".format(self.ShareKey, self.Name))
    

    def __init__(self, **kwargs):

        if ("GPUsPerRank" in kwargs) and ("RanksPerGPU" in kwargs):
            CompositionLogger.RaiseError(AttributeError, "Only set one of GPUsPerRank and RanksPerGPU")
        
        for key in kwargs:
            if key not in self.__class__.__dict__:
                CompositionLogger.RaiseError(AttributeError, "{0} is not an Application initializer".format(key))
            else:
                self.__setattr__(key, kwargs[key])
                
        # Set the rest to the defaults in the class definition
        for key in self.__class__.__dict__:
            if key.startswith("__") and key.endswith("__"):
                continue
            elif callable(self.__class__.__dict__[key]):
                continue
            elif key not in self.__dict__:
                self.__setattr__(key, self.__class__.__dict__[key])
            
    
    def __setattr__(self, name, value):
        if (name in ("Ranks")) and (type(value) is not int):
            CompositionLogger.RaiseError(ValueError, "{0} should be set as an int".format(name))
        if (name in ("Ranks", "RanksPerNode", "CoresPerRank")) and (value is not None) and (type(value) is not int):
            CompositionLogger.RaiseError(ValueError, "{0} should be set as an int".format(name))
        if (name in ("GPUsPerRank", "RanksPerGPU")) and (value is not None) and (type(value) is not int) and (type(value) is not str):
            CompositionLogger.RaiseError(ValueError, "{0} should be set as an int or a string".format(name))
        if (name in ("Filepath", "SetupFile", "Name")) and (value is not None) and (type(value) is not str):
            CompositionLogger.RaiseError(AttributeError, "{0} should be set as a string".format(name))
        if (name in ("Environment")) and (type(value) is not dict):
            CompositionLogger.RaiseError(ValueError, "{0} should be set as a dictionary".format(name))

        if name in ["CommandLineArguments", "MPIRunnerArguments"]:
            self.__dict__[name] = effis.composition.arguments.Arguments(value)
        elif name == "Input":
            self.__dict__[name] = effis.composition.input.InputList(value)
        else:
            self.__dict__[name] = value

    
    def _add_(self, other, reverse=False):
        
        if type(other) is type(self):
            left = [self]
            right = [other]
        elif type(other) is list:
            for i in range(len(other)):
                if type(other[i]) is not type(self):
                    CompositionLogger.RaiseError(ValueError, "List elements to add as applications must be of type effis.composition.Application")
            left = [self]
            right = other            
        else:
            CompositionLogger.RaiseError(ValueError, "Can only add applications and/or lists of them with elements of type effis.composition.Application")

        if reverse:
            return right + left
        else:
            return left + right
        
    
    def __radd__(self, other):
        return self._add_(other, reverse=True)
        
    
    def __add__(self, other):
        return self._add_(other)



        