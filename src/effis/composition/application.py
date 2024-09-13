"""
effis.composition.application
"""

import copy
from effis.composition.runner import Detected, UseRunner
from effis.composition.arguments import Arguments
from effis.composition.input import InputList
from effis.composition.log import CompositionLogger


class DependsClass(Arguments):

    def __init__(self, value):
        if isinstance(value, type(self)):
            self.arguments = value.arguments
        elif (not isinstance(value, Application)) and (not isinstance(value, list)):
            CompositionLogger.RaiseError(ValueError, "DependsOn must be given as an Application or a list of them (or another DependsClass object)")
        elif isinstance(value, list):
            self.arguments = value
        elif isinstance(value, Application):
            self.arguments = [value]


    def __iadd__(self, value):
        if isinstance(value, type(self)):
            self.arguments = self.arguments + value.arguments
        elif (not isinstance(value, Application)) and (not isinstance(value, list)):
            CompositionLogger.RaiseError(ValueError, "DependsOn must be given as an Application or a list of them")
        elif isinstance(value, list):
            self.arguments = self.arguments + value
        elif isinstance(value, Application):
            self.arguments = self.arguments + [value]

        return self



class Application(UseRunner):
    """
    An Application is an executable to run.
    One or more are added to Workflow.
    """

    #: Set a name for the Application (which defines subdirectory name)
    Name = None

    #: Path to application executable
    cmd = None

    #: Appliction command line arguments
    CommandLineArguments = []

    #: Custom MPI launcher settings; bypasses setting with Runner
    MPIRunnerArguments = []
    
    #: A file to source before lanuching the application (for environment setup, etc.)
    SetupFile = None

    #: Set environment variables with Python dictionary (instead of setup file); Not implemented yet
    Environment = {}

    #: This application depends on others finishing
    DependsOn = []

    #: Input files to copy for the Application
    Input = []

    _RunnerError_ = (CompositionLogger.RunnerError, "No MPI [Application] Runner found. Exiting...")

    """
    #ShareKey = None
    Ranks = 1
    RanksPerNode = None
    CoresPerRank = None
    GPUsPerRank = None
    RanksPerGPU = None
    """

    
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
        elif ('RanksPerGPU' in self.__dict__) and (self.RanksPerGPU is not None) and (type(self.RanksPerGPU) is int):
            ranknum = app.RanksPerGPU
            gpunum = 1
        elif ('RanksPerGPU' in self.__dict__) and (self.RanksPerGPU is not None) and (type(self.RanksPerGPU) is str):
            ranknum, gpunum = app.RanksPerGPU.split(":")
            ranknum = int(ranknum.strip())
            gpunum = int(gpunum.strip())
        return gpunum, ranknum
    

    @classmethod
    def CheckApplications(cls, other):
        if type(other) is list:
            for i in range(len(other)):
                if not isinstance(other[i], cls):
                    CompositionLogger.RaiseError(ValueError, "List elements to add as applications must be of type Application")
        elif not isinstance(other, cls):
            CompositionLogger.RaiseError(ValueError, "Can only add applications and/or lists of them with elements of type Application")
        return other


    def GetCall(self):
        RunnerArgs = []
        if self.Runner is not None:
            RunnerArgs = self.Runner.GetCall(self, self.MPIRunnerArguments)
        Cmd = RunnerArgs + [self.cmd] + self.CommandLineArguments.arguments
        return Cmd


    @staticmethod
    def AutoRunner():
        return Detected.Runner
    
    
    def __setattr__(self, name, value):

        # Warn if setting something unknown
        if name not in self.__dir__():
            CompositionLogger.Warning("{0} not recognized as Application attribute".format(name))

        # Throw errors for bad attribute type settings
        if (name in ("cmd", "SetupFile", "Name")) and (value is not None) and (type(value) is not str):
            CompositionLogger.RaiseError(AttributeError, "{0} should be set as a string".format(name))
        if (name in ("Environment")) and (type(value) is not dict):
            CompositionLogger.RaiseError(ValueError, "{0} should be set as a dictionary".format(name))

        if name in ["CommandLineArguments", "MPIRunnerArguments"]:
            self.__dict__[name] = Arguments(value)
        elif name == "Input":
            self.__dict__[name] = InputList(value)
        elif (name == "DependsOn"):
            self.__dict__[name] = DependsClass(value)
        else:
            self.__dict__[name] = value

    
    def _add_(self, other, reverse=False):
        
        if isinstance(other, Application):
            left = [self]
            right = [other]
        elif type(other) is list:
            for i in range(len(other)):
                if not isinstance(other[i], Application):
                    CompositionLogger.RaiseError(ValueError, "List elements to add as applications must be of type Application")
            left = [self]
            right = other            
        else:
            CompositionLogger.RaiseError(ValueError, "Can only add applications and/or lists of them with elements of type Application")

        if reverse:
            return right + left
        else:
            return left + right
        
    
    def __radd__(self, other):
        return self._add_(other, reverse=True)
        
    
    def __add__(self, other):
        return self._add_(other)


"""
class LoginNodeApplication(Application):

    def __init__(self, **kwargs):

        self.UseNodes = 0

        for  key in ["Ranks", "RanksPerNode", "CoresPerRank", "GPUsPerRank", "RanksPerGPU", "ShareKey", "MPIRunnerArguments", "__class__"]:
            if key in kwargs:
                CompositionLogger.RaiseError(ValueError, "Setting {0} is not allowed with LoginNodeApplication.".format(key))
        if ("UseNodes" in kwargs) and (type(kwargs["UseNodes"]) is int):
            self.UseNodes = kwargs["UseNodes"]
            del kwargs["UseNodes"]
        elif ("UseNodes" in kwargs):
            CompositionLogger.RaiseError(ValueError, "UseNodes value must be an integer")

        #Application.__init__(self, **kwargs)
        super(LoginNodeApplication, self).__init__(__class__=Application, **kwargs)
"""
