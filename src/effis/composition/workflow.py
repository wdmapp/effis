"""
effis.composition.workflow
"""

import socket
import datetime
import os
import getpass
import subprocess
import json
import sys
import getpass
import dill as pickle

import codar.savanna

import effis.composition.node
import effis.composition.application
import effis.composition.arguments
import effis.composition.input
import effis.composition.campaign
from effis.composition.log import CompositionLogger

ExamplesPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Examples"))


class Workflow:
    """
    Add one or more Applications to a compose a Workflow.
    """
    
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
    Backup = None
    

    def __init__(self, **kwargs):

        # Fixed labels
        self.__dict__['SweepGroupLabel'] = "EFFIS"
        self.__dict__['IterationLabel'] = 'run-0.iteration-0'

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
        elif name == "Backup":
            self.__dict__[name] = effis.composition.backup.Backup(value)
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
            if (name in ("Name", "ParentDirectory")) and (self.Name is not None) and (self.ParentDirectory is not None):
                if "WorkflowDirectory" in self.__dict__:
                    CompositionLogger.Warning("Changing Name or ParentDirectory after they've both been set can break referencing (Workflow)Directory before Create()")
                self.SetWorkflowDirectory()

    
    # Use (workflow += application) as an intuitive way to build the workflow with applications
    def __iadd__(self, other):
        if isinstance(other, effis.composition.application.Application) or (type(other) is list):
            self.__dict__['Applications'] =  self.Applications + other

            if "WorkflowDirectory" in self.__dict__:
                if isinstance(other, effis.composition.application.Application):
                    newother = [other]
                else:
                    newother = other
                self.SetAppDirectories(newother)

            return self
        else:
            CompositionLogger.RaiseError(ValueError, "Only effis.composition.Application objects can be added to a Workflow object")


    # Make sure the machine exists in Cheetah
    def _Machine_(self, mach=None):

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
            exceptions = ["perlmutter"]
            if machine.lower() in exceptions:
                self.__dict__['Machine'] = machine.lower()
            else:
                CompositionLogger.RaiseError(ValueError, "Cannot find machine = {0}".format(machine))


    def SetWorkflowDirectory(self):
        self.__dict__["WorkflowDirectory"] = os.path.join(self.ParentDirectory, self.Name)
        if self.TimeIndex:
            self.__dict__["WorkflowDirectory"] = "{0}.{1}".format(self.WorkflowDirectory, datetime.datetime.now().strftime('%Y-%m-%d.%H.%M.%S'))
        self.__dict__["WorkflowDirectory"] = os.path.abspath(self.__dict__["WorkflowDirectory"])
        self.__dict__['Directory'] = os.path.abspath(os.path.join(self.WorkflowDirectory, getpass.getuser(), self.SweepGroupLabel, self.IterationLabel))


    def SetAppDirectories(self, applications):
        for app in applications:
            app.__dict__['Directory'] = self.Directory
            if self.Subdirs:
                app.__dict__['Directory'] = os.path.join(app.Directory, app.Name)
            
    
    def Create(self):

        if (self.Name is None) and (self.ParentDiretory is None):
            CompositionLogger.RaiseError(AttributeError, "Must set at least one of Name or ParentDirectory for a Workflow")
        elif self.ParentDirectory is None:
            self.ParentDirectory = "./"
        elif self.Name is None:
            self.Name = os.path.basename(self.ParentDirectory)

        if self.Machine is None:
            self._Machine_()

        self.SetWorkflowDirectory()

        if os.path.exists(self.WorkflowDirectory):
            CompositionLogger.RaiseError(FileExistsError, "Trying to create to a directory that already exists: {0}".format(self.WorkflowDirectory))

        campaign = effis.composition.campaign.Campaign(self)
        print("Created:", self.WorkflowDirectory)

        # Store data (serialize)
        with open(os.path.join(self.WorkflowDirectory, 'workflow.pickle'), 'wb') as handle:
            pickle.dump(self, handle, protocol=pickle.HIGHEST_PROTOCOL)

        for app in self.Applications:
            linkpath = os.path.join(self.WorkflowDirectory, os.path.basename(app.Directory))
            if not os.path.exists(linkpath):
                os.symlink(app.Directory, linkpath)


    def Submit(self, rerun=False):

        touchname = os.path.join(os.path.dirname(self.post_script), ".backup.ready")

        # If forcing a rerun, remove the .backup.ready file if it's there
        if rerun:
            if os.path.exists(touchname):
                os.remove(touchname)
            wfile = os.path.join(self.WorkflowDirectory, getpass.getuser(), "EFFIS", "codar.workflow.status.json")
            if os.path.exists(wfile):
                with open(wfile) as infile:
                    config = json.load(infile)
                if config[self.IterationLabel]["state"] != codar.savanna.status.NOT_STARTED:
                    config[self.IterationLabel]["state"] = codar.savanna.status.NOT_STARTED
                    with open(wfile, "w") as outfile:
                        json.dump(config, outfile, ensure_ascii=False, indent=4)

        if len(self.Backup.destinations) > 0:
            with open(self.post_script, "a+") as outfile:
                outfile.write("touch {0}\n".format(touchname))

            outdict = {
                'readyfile': touchname,
                'source': self.Backup .source,
                'endpoints': {},
            }
            for endpoint in self.Backup.destinations:
                outdict['endpoints'][endpoint] = {
                    'id': self.Backup.destinations[endpoint].Endpoint,
                    'paths': [],
                }
                for entry in self.Backup.destinations[endpoint].Input.list:
                    entrydict = {}
                    for key in ('inpath', 'outpath', 'link', 'rename'):
                        entrydict[key] = entry.__dict__[key]
                    outdict['endpoints'][endpoint]['paths'] += [entrydict]

            jsonname = os.path.join(os.path.dirname(self.post_script), "backup.json")
            with open(jsonname, "w") as outfile:
                json.dump(outdict, outfile, ensure_ascii=False, indent=4)


            # Start the globus process here
            scriptname = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "runtime", "BackupGlobus.py"))
            #cmd = ["python3", scriptname, jsonname, "--checkdest"]
            cmd = ["python3", scriptname, jsonname]
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, shell=False)

            error = False
            for line in iter(p.stderr.readline, b''):
                if line.decode("utf-8").rstrip() == "STATUS=READY":
                    break
                elif line.decode("utf-8").rstrip() != "":
                    print(line.decode("utf-8"), file=sys.stderr, end="")
                    error = True
            if error:
                sys.exit(1)

            p.stderr = sys.stderr

        shpath = os.path.join(self.WorkflowDirectory, getpass.getuser(), "run-all.sh")
        print("Called: ", shpath)
        subprocess.call([shpath])

