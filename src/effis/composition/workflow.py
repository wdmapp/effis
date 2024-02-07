import socket
import datetime
import os

import codar.savanna

import effis.composition.node
import effis.composition.application
import effis.composition.arguments
import effis.composition.input
import effis.composition.campaign
from effis.composition.log import CompositionLogger

ExamplesPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Examples"))


class Workflow:
    
    Name = None
    ParentDirectory = None
    
    Walltime = datetime.timedelta(hours=1)
    SetupFile = None

    TimeIndex = False
    Subdirs = True
    MPMD = False
    
    Machine = None
    Node = None
    
    Queue = None
    Charge = None
    Reservation = None
    SchedulerDirectives = []

    Applications = []
    Input = []
    

    def __init__(self, **kwargs):

        # Set what's given in keyword arguments by user
        for key in kwargs:
            if key not in self.__class__.__dict__:
                CompositionLogger.RaiseError(AttributeError, "{0} is not a Workflow initializer".format(key))
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
        if name not in self.__class__.__dict__:
            CompositionLogger.Warning("{0} not recognized as Workflow attribute".format(name))
        
        if (name in ("Name", "ParentDirectory", "Machine", "Queue", "Charge", "Reservation", "SetupFile")) and (value is not None) and (type(value) is not str):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a string".format(name))
        elif name in ("Subdirs", "MPMD", "TimeIndex") and (type(value) is not bool):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a boolean".format(name))
        elif (name == "Node") and (value is not None) and (type(value) is not effis.composition.node.Node):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as an effis.composition.Node".format(name))
        elif (name == "Walltime") and (type(value) is not datetime.timedelta):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a datetime.timedelta".format(name))

        if name == "SchedulerDirectives":
            self.__dict__[name] = effis.composition.arguments.Arguments(value)  # Arguments does the type check
        elif name == "Input":
            self.__dict__[name] = effis.composition.input.InputList(value)           
        elif name == "Applications":
            self.__dict__[name] = effis.composition.application.Application.CheckApplications(value)  # Also does the type check
        elif (name == "Machine") and (value is not None):
            self._Machine_(value)
        elif (name == "MPMD") and value and self.Subdirs:            
            self.__dict__[name] = value
            self.Subdirs = False
            CompositionLogger.Info("Setting Subdirs=False because it is required with MPMD=True")
        elif (name == "Subdirs") and value and self.MPMD:
            CompositionLogger.Warning("Cannot set subdirs=True because MPMD=True")
        else:
            self.__dict__[name] = value

    
    # Use (workflow += application) as an intuitive way to build the workflow with applications
    def __iadd__(self, other):
        if (type(other) is effis.composition.application.Application) or (type(other) is list):
            self.__dict__['Applications'] =  self.Applications + other
            return self
        else:
            CompositionLogger.RaiseError(ValueError, "Only effis.composition.Application objects can be added to a Workflow object")


    # Make sure the machine exists in Cheetah
    def _Machine_(self, mach):

        known = []
        for name in codar.savanna.machines.__dict__:
            if type(codar.savanna.machines.__dict__[name]) is codar.savanna.machines.Machine:
                known += [name]

        # If no machine has been set, try to find it based on the local host name
        if mach is None:
            machine = socket.gethostname().lower()
            CompositionLogger.Info("Found {0} as the local host".format(machine))
        else:
            machine = mach.lower()
        
        for name in known:
            if machine.find(name) != -1:
                self.__dict__['Machine'] = name
                break

        if machine not in known:
            CompositionLogger.RaiseError(ValueError, "Cannot find machine = {0}".format(machine))
            
    
    def Create(self):

        if (self.Name is None) and (self.ParentDiretory is None):
            CompositionLogger.RaiseError(AttributeError, "Must set at least one of Name or ParentDirectory for a Workflow")
        elif self.ParentDirectory is None:
            self.ParentDirectory = "./"
        elif self.Name is None:
            self.Name = os.path.basename(self.ParentDirectory)

        if self.Machine is None:
            self._Machine_()
        
        self.__dict__["WorkflowDirectory"] = os.path.join(self.ParentDirectory, self.Name)
        if self.TimeIndex:
            self.__dict__["WorkflowDirectory"] = "{0}.{1}".format(self.WorkflowDirectory, datetime.datetime.now().strftime('%Y-%m-%d.%H.%M.%S'))

        if os.path.exists(self.WorkflowDirectory):
            CompositionLogger.RaiseError(FileExistsError, "Trying to create to a directory that already exists: {0}".format(self.WorkflowDirectory))

        campaign = effis.composition.campaign.Campaign(self)
