"""
effis.composition.workflow
"""

import datetime
import os
import subprocess
import json
import sys
import shutil
import stat
import atexit
from contextlib import ContextDecorator
import dill as pickle

from effis.composition.runner import Detected, UseRunner
from effis.composition.application import Application
from effis.composition.arguments import Arguments
from effis.composition.input import InputList
from effis.composition.backup import Backup
from effis.composition.log import CompositionLogger


# This is just for convenience with examples
ExamplesPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Examples"))



class Chdir(ContextDecorator):

    def __init__(self, directory):
        self.newdir = directory
        self.olddir = os.getcwd()


    def __enter__(self):
        os.chdir(self.newdir)
        return self


    def __exit__(self, *exc):
        os.chdir(self.olddir)
        return None


def InputCopy(setup):
    
    for item in setup.Input.list:
        outpath = setup.Directory
        if item.outpath is not None:
            outpath = os.path.join(outpath, item.outpath)
            if not os.path.exists(outpath):
                os.makedirs(outpath)
        if item.rename is not None:
            outpath = os.path.join(outpath, item.rename)
        else:
            outpath = os.path.join(outpath, os.path.basename(item.inpath))
        
        if item.link:
            os.symlink(os.path.abspath(item.inpath), outpath)
        else:
            if os.path.isdir(item.inpath):
                shutil.copytree(item.inpath, outpath)
            else:
                shutil.copy(item.inpath, outpath)

    if setup.SetupFile is not None:
        outpath = setup.Directory
        shutil.copy(setup.SetupFile, outpath)
        setup.SetupFile = os.path.basename(setup.SetupFile)


class Workflow(UseRunner):
    """
    Add one or more Applications to a compose a Workflow.
    """

    #: Set a name for the workflow
    Name = None

    #: The workflow will be crated/run in ParentDirectory/Name
    ParentDirectory = None

    #: A file to source for environment setup, etc.
    SetupFile = None

    #: Custom scheduler directives; bypasses setting with Runner
    SchedulerDirectives = []

    #: Holds the appliations of the Workflow
    Applications = []

    #: Holds input files
    Input = []

    #: Items to copy between endpoints after the job
    Backup = None

    # Signals workflow finished, can run backup
    touchname = "workflow.done"
    backupname = "backup.json"
    submitname = "workflow.sh"


    # Might get rid of this
    TimeIndex = False

    # Haven't really tried with these
    Subdirs = True
    MPMD = False

    __RunnerError__ = (CompositionLogger.Warning, "No batch queue [Workflow] Runner found, conintuining without one.")


    """ These are now Runner specific and set there

    #: The maximum run time. (This is not necessary without a scheduler, but will cause time outs)
    Walltime = datetime.timedelta(hours=1)

    #: Account to charge
    Charge = None

    Queue = None
    Reservation = None
    """

    
    def __setattr__(self, name, value):

        if name not in self.__dir__():
            CompositionLogger.Warning("{0} not recognized as Workflow attribute".format(name))
        
        if (name in ("Name", "ParentDirectory", "SetupFile")) and (value is not None) and (type(value) is not str):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a string".format(name))
        elif name in ("Subdirs", "MPMD", "TimeIndex") and (type(value) is not bool):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a boolean".format(name))

        if name == "SchedulerDirectives":
            self.__dict__[name] = Arguments(value)  # Arguments does the type check
        elif name == "Input":
            self.__dict__[name] = InputList(value)
        elif name == "Backup":
            self.__dict__[name] = Backup(value)
        elif name == "Applications":
            self.__dict__[name] = Application.CheckApplications(value)  # Also does the type check
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
        if isinstance(other, Application) or (type(other) is list):
            self.__dict__['Applications'] =  self.Applications + other

            if "WorkflowDirectory" in self.__dict__:
                if isinstance(other, Application):
                    newother = [other]
                else:
                    newother = other
                self.SetAppDirectories(newother)

            return self
        else:
            CompositionLogger.RaiseError(ValueError, "Only Application objects can be added to a Workflow object")


    @staticmethod
    def AutoRunner():
        return Detected.System


    def Application(self, **kwargs):
        if ('Runner' not in kwargs):
            thisrunner = Application.DetectRunnerInfo(useprint=True)
            CompositionLogger.Info("Application ({0}): Using detected runner {1}".format(UseRunner.kwargsmsg(kwargs), thisrunner.cmd))
            kwargs['Runner'] = thisrunner
        self += Application(**kwargs)
        return self.Applications[-1]


    def GetCall(self):
        RunnerArgs = []
        if self.Runner is not None:
            RunnerArgs = self.Runner.GetCall(self, self.SchedulerDirectives)
        return RunnerArgs


    def SetWorkflowDirectory(self):
        self.__dict__["WorkflowDirectory"] = os.path.join(self.ParentDirectory, self.Name)
        if self.TimeIndex:
            self.__dict__["WorkflowDirectory"] = "{0}.{1}".format(self.WorkflowDirectory, datetime.datetime.now().strftime('%Y-%m-%d.%H.%M.%S'))
        self.__dict__["WorkflowDirectory"] = os.path.abspath(self.__dict__["WorkflowDirectory"])
        self.__dict__['Directory'] = self.WorkflowDirectory


    def SetAppDirectories(self, applications):
        for app in applications:
            app.__dict__['Directory'] = self.Directory
            if self.Subdirs:
                app.__dict__['Directory'] = os.path.join(app.Directory, app.Name)
    

    def PickleWrite(self):
        """
        Write the workflow to a pickle file
        """

        with open(os.path.join(self.WorkflowDirectory, 'workflow.pickle'), 'wb') as handle:
            pickle.dump(self, handle, protocol=pickle.HIGHEST_PROTOCOL, recurse=True)

    
    def Create(self):
        """
        Create the Workflow description and copy associated files to the run directories
        """

        if (self.Name is None) and (self.ParentDiretory is None):
            CompositionLogger.RaiseError(AttributeError, "Must set at least one of Name or ParentDirectory for a Workflow")
        elif self.ParentDirectory is None:
            self.ParentDirectory = "./"
        elif self.Name is None:
            self.Name = os.path.basename(self.ParentDirectory)

        # May already be set, but call in case not
        self.SetWorkflowDirectory()
        self.SetAppDirectories(self.Applications)

        # Create Directories
        if os.path.exists(self.WorkflowDirectory):
            CompositionLogger.RaiseError(FileExistsError, "Trying to create to a directory that already exists: {0}".format(self.WorkflowDirectory))
        os.makedirs(self.WorkflowDirectory)
        CompositionLogger.Info("Created: {0}".format(self.WorkflowDirectory))
        for app in self.Applications:
            if not os.path.exists(app.Directory):
                os.makedirs(app.Directory)

        # Copy the input files
        InputCopy(self)
        for app in self.Applications:
            InputCopy(app)

        # Check for cyclic dependencies
        apps = {}
        for app in self.Applications:
            apps[app.Name] = {}
            apps[app.Name]['complete'] = False
            for dep in app.DependsOn:
                depdeps = dep.DependsOn
                for depdep in depdeps:
                    if app.Name == depdep.Name:
                        CompositionLogger.RaiseError(ValueError, "Cyclic dependencies between {0} and {1}".format(app.Name, dep.Name))

        # Done file in workflow directory
        self.touchname = os.path.join(self.Directory, self.touchname)
        self.backupname = os.path.join(self.Directory, self.backupname)
        self.submitname = os.path.join(self.Directory, self.submitname)
        #self.SetupBackup()

        # Store data (serialize)
        #self.PickleWrite()
        atexit.register(self.PickleWrite)


    def SetupBackup(self):

        if len(self.Backup.destinations) > 0:

            if self.Backup.source is None:
                self.Backup.SetSourceEndpoint()

            self.BackupDict = {
                'readyfile': self.touchname,
                'source': self.Backup.source,
                'recursive_symlinks': self.Backup.recursive_symlinks,
                'endpoints': {},
            }
            for endpoint in self.Backup.destinations:
                self.BackupDict['endpoints'][endpoint] = {
                    'id': self.Backup.destinations[endpoint].Endpoint,
                    'paths': [],
                }
                for entry in self.Backup.destinations[endpoint].Input.list:
                    entrydict = {}
                    for key in ('inpath', 'outpath', 'link', 'rename'):
                        entrydict[key] = entry.__dict__[key]
                    self.BackupDict['endpoints'][endpoint]['paths'] += [entrydict]

            with open(self.backupname, "w") as outfile:
                json.dump(self.BackupDict, outfile, ensure_ascii=False, indent=4)


    def SubmitBackup(self):

        if len(self.Backup.destinations) > 0:

            # Start the globus process here
            scriptname = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "runtime", "BackupGlobus.py"))

            #cmd = ["python3", scriptname, jsonname, "--checkdest"]
            cmd = ["python3", scriptname, self.backupname]
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE)

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


    def Submit(self, rerun=False):

        with Chdir(self.Directory):
            if os.path.exists(self.touchname):
                os.remove(self.touchname)

        self.SetupBackup()
        self.SubmitBackup()

        SubmitCall = self.GetCall()
        if len(SubmitCall) > 0:
            SubmitCall += [self.submitname]
            with open(self.submitname, 'w') as outfile:
                outfile.write("#!/bin/sh" + "\n")
                outfile.write("effis-submit --sub {0}".format(self.Directory))
            subprocess.run(SubmitCall)
        else:
            self.SubSubmit()


    def SubSubmit(self):

        apps = []
        for app in self.Applications:
            pwd = os.getcwd()

            with Chdir(app.Directory):

                cmd = app.GetCall()
                CompositionLogger.Info("Running: {0}".format(" ".join(cmd)))

                if app.SetupFile is not None:
                    jobfile = "./{0}.sh".format(app.Name)
                    with open(jobfile, "w") as outfile:
                        outfile.write("#!/bin/sh" + "\n")
                        outfile.write(". {0}".format(app.SetupFile) + "\n")
                        outfile.write("{0}".format(" ".join(cmd)))
                    os.chmod(
                        jobfile,
                        stat.S_IRUSR | stat.S_IXUSR | stat.S_IWUSR |
                        stat.S_IRGRP | stat.S_IXGRP |
                        stat.S_IROTH | stat.S_IXOTH
                    )
                    p = subprocess.Popen([jobfile])
                else:
                    p = subprocess.Popen(cmd)

                apps += [p]

        for app in apps:
            p.wait()

        with Chdir(self.Directory):
            with open(self.touchname, "w") as outfile:
                outfile.write("")


