"""
effis.composition.application
"""

from effis.composition.runner import Detected, UseRunner
from effis.composition.log import CompositionLogger

#from effis.composition.arguments import Arguments
#from effis.composition.input import InputList
from effis.composition.util import ListType, Arguments, InputList


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

    #: Send the Application's terminal output to a file
    LogFile = None

    #: Set environment variables with Python dictionary (instead of setup file); Not implemented yet
    Environment = {}

    #: This application depends on others finishing
    DependsOn = []

    #: Input files to copy for the Application
    Input = []

    _RunnerError_ = (CompositionLogger.RunnerError, "No MPI [Application] Runner found. Exiting...")

    #: Lets set a max running for the group
    Group = None


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
        Cmd = RunnerArgs + [self.cmd] + self.CommandLineArguments.List
        return Cmd


    @staticmethod
    def AutoRunner():
        return Detected.Runner
    
    
    def setattr(self, name, value):
        """
        Attribute setting; due to inheritance, names are guaranteed to be in the class
        """

        # Throw errors for bad attribute type settings
        if (name in ("cmd", "SetupFile", "Name", "Group")) and (value is not None) and (type(value) is not str):
            CompositionLogger.RaiseError(AttributeError, "{0} should be set as a string".format(name))
        if (name in ("Environment")) and (type(value) is not dict):
            CompositionLogger.RaiseError(ValueError, "{0} should be set as a dictionary".format(name))

        if name in ["CommandLineArguments", "MPIRunnerArguments"]:
            super(UseRunner, self).__setattr__(name, Arguments(value, key=name))
        elif name == "Input":
            super(UseRunner, self).__setattr__(name, InputList(value, key=name))
        elif (name == "DependsOn"):
            super(UseRunner, self).__setattr__(name, ListType(value, Application, key=name))
        else:
            super(UseRunner, self).__setattr__(name, value)


    """
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

