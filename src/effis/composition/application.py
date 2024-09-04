"""
effis.composition.application
"""

import effis.composition.arguments
import effis.composition.input
import effis.composition.node
from effis.composition.log import CompositionLogger

import copy


class Application:
    """
    An Application is an executable to run.
    One or more are added to Workflow.
    """

    #: Set a name for the Application (which defines subdirectory name)
    Name = None

    #: Path to application executable
    Filepath = None

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
                    CompositionLogger.RaiseError(ValueError, "List elements to add as applications must be of type effis.composition.Application")
        elif not isinstance(other, cls):
            CompositionLogger.RaiseError(ValueError, "Can only add applications and/or lists of them with elements of type effis.composition.Application")
        return other


    def GetCall(self):
        RunnerArgs = []
        if self.Runner is not None:
            RunnerArgs = self.Runner.GetCall(self, self.MPIRunnerArguments)
        Cmd = RunnerArgs + [self.Filepath] + self.CommandLineArguments.arguments
        return Cmd
    

    def __init__(self, **kwargs):

        if "Runner" not in kwargs:
            CompositionLogger.Warning("Runner was not set with Application **kwargs={0}".format(kwargs))
            self.__dict__['Runner'] = effis.composition.runner.DetectRunnerInfo(obj=self, useprint=False)
            if self.Runner is None:
                CompositionLogger.RaiseError(ValueError, "No Runner was detected and a Runner must be set with an Application")
            CompositionLogger.Info("Using detected runner {0}".format(self.Runner.cmd))
        else:
            self.__dict__['Runner'] = kwargs['Runner']
            del kwargs['Runner']

        if self.Runner is not None:
            for key in self.Runner.options:
                self.__dict__[key] = None


        if "__class__" in kwargs:
            kwobj = kwargs["__class__"]
            del kwargs["__class__"]
        else:
            kwobj = self.__class__

        for key in kwargs:
            if (key not in kwobj.__dict__) and (key not in self.__dict__):
                CompositionLogger.RaiseError(AttributeError, "{0} is not an initializer for Application(**kwargs={1}) using Runner={2}".format(key, kwargs, str(self.Runner)))
            else:
                self.__setattr__(key, kwargs[key])
                
        # Set the rest to the defaults in the class definition
        for key in kwobj.__dict__:
            if key.startswith("__") and key.endswith("__"):
                continue
            elif callable(kwobj.__dict__[key]):
                continue
            elif key not in self.__dict__:
                self.__setattr__(key, kwobj.__dict__[key])
            
    
    def __setattr__(self, name, value):

        if (name in ("Filepath", "SetupFile", "Name")) and (value is not None) and (type(value) is not str):
            CompositionLogger.RaiseError(AttributeError, "{0} should be set as a string".format(name))
        if (name in ("Environment")) and (type(value) is not dict):
            CompositionLogger.RaiseError(ValueError, "{0} should be set as a dictionary".format(name))
        if (name == "DependsOn") and (value is not None) and not (isinstance(value, type(self)) or isinstance(value, list)):
            CompositionLogger.RaiseError(ValueError, "{0} should be set as an Application (or list of Applications)".format(name))

        if name in ["CommandLineArguments", "MPIRunnerArguments"]:
            self.__dict__[name] = effis.composition.arguments.Arguments(value)
        elif name == "Input":
            self.__dict__[name] = effis.composition.input.InputList(value)
        elif (name == "DependsOn"):
            if isinstance(value, type(self)):
                self.__dict__[name] = [value]
            elif isinstance(value, list):
                self.__dict__[name] = value
        else:
            self.__dict__[name] = value

    
    def _add_(self, other, reverse=False):
        
        if isinstance(other, Application):
            left = [self]
            right = [other]
        elif type(other) is list:
            for i in range(len(other)):
                if not isinstance(other[i], Application):
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

