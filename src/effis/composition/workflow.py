"""
effis.composition.workflow
"""

import datetime
import os
import subprocess
import threading
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


class Chdir(ContextDecorator):
    """
    Context manager that works with Python's with statement – changes directory and then returns
    """

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

    #: The workflow will be created/run in Directory
    Directory = None

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

    #: Run Applications in subdirectories
    Subdirs = True

    # Use MPI MPMD; not supported yet
    MPMD = False

    # Appends the current time to the created workflow directory (Might get rid of this)
    TimeIndex = False

    # Various workflow files
    touchname = "workflow.done"     # Signals workflow finished, can run backup
    backupname = "backup.json"      # Configures the globus movement
    submitname = "workflow.sh"      # File that submits with scheduler
    picklename = "workflow.pickle"  # Saves workflow description

    # Used with checking for the Runner
    _RunnerError_ = (CompositionLogger.Warning, "No batch queue [Workflow] Runner found, conintuining without one.")

    # Used to make sure Create() is called before Submit()
    _CreateCalled_ = False


    
    def __setattr__(self, name, value):

        # Warn if setting something unknown
        if name not in self.__dir__():
            CompositionLogger.Warning("{0} not recognized as Workflow attribute".format(name))

        # Throw errors for bad attribute type settings
        if (name in ("Name", "Directory", "SetupFile")) and (value is not None) and (type(value) is not str):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a string".format(name))
        elif name in ("Subdirs", "MPMD", "TimeIndex") and (type(value) is not bool):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a boolean".format(name))

        # These are for Object types, will throw errors within if necessary
        if name == "SchedulerDirectives":
            self.__dict__[name] = Arguments(value)  # Arguments does the type check
        elif name == "Input":
            self.__dict__[name] = InputList(value)
        elif name == "Backup":
            self.__dict__[name] = Backup(value)
        elif name == "Applications":
            self.__dict__[name] = Application.CheckApplications(value)  # Also does the type check

        # Check for some other conditions that don't make sense; don't set anything
        elif (name == "MPMD") and value:
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} is not supported yet".format(name))
        elif (name == "Subdirs") and value and self.MPMD:
            CompositionLogger.Warning("Cannot set subdirs=True because MPMD=True")

        # Will use  self.__dict__[name] = value
        else:

            if (name == "MPMD") and value and self.Subdirs:
                CompositionLogger.Info("Setting Subdirs=False because it is required with MPMD=True")
                self.Subdirs = False

            if (name in ("Subdir", "MPMD")) and (len(self.Applications) > 0):
                CompositionLogger.Warning("Changing Subdir or MPMD after Application(s) have been added to a Workflow can break referencing Directory before Create()")
            elif (name == "Directory") and (self.Directory is not None):
                CompositionLogger.Warning("Changing Directory after it's been set can break referencing Directory before Create()")

            self.__dict__[name] = value

            if (name == "Directory") and (self.Directory is not None):
                self.SetWorkflowDirectory()


    
    def __iadd__(self, other):
        """
        Meant as an intuitive way to build the workflow by adding applications; takes single applications or lists:
        – workflow += application 
        – workflow += [app1, app2]
        """

        if isinstance(other, Application) or (type(other) is list):
            self.__dict__['Applications'] =  self.Applications + other

            if "Directory" in self.__dict__:
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
        """
        Create Application in the workflow
        """

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
        if self.TimeIndex:
            self.__dict__["Directory"] = "{0}.{1}".format(self.Directory, datetime.datetime.now().strftime('%Y-%m-%d.%H.%M.%S'))
        self.__dict__["Directory"] = os.path.abspath(self.Directory)


    def SetAppDirectories(self, applications):
        for app in applications:
            app.__dict__['Directory'] = self.Directory
            if self.Subdirs and (app.Name is not None):
                app.__dict__['Directory'] = os.path.join(app.Directory, app.Name)
    

    def PickleWrite(self):
        """
        Write the workflow to a pickle file
        """

        with open(os.path.join(self.Directory, self.picklename), 'wb') as handle:
            pickle.dump(self, handle, protocol=pickle.HIGHEST_PROTOCOL, recurse=True)

    
    def Create(self):
        """
        Create the Workflow description and copy associated files to the run directories
        """

        if (self.Name is None) and (self.Directory is None):
            CompositionLogger.RaiseError(AttributeError, "Must set at least one of Name or Directory for a Workflow")
        elif self.Name is None:
            self.Name = os.path.basename(self.Directory)
        elif self.Directory is None:
            self.Directory = "./"

        # May already be set, but call in case not
        self.SetWorkflowDirectory()

        # Check things that don't make really make sense for applications
        for i, app in enumerate(self.Applications):
            
            if app.cmd is None:
                CompositionLogger.RaiseError(AttributeError, "Cannot use an Application (#{0}) with no cmd attribute".format(i))

            if app.Name is None:
                app.Name = os.path.basename(app.cmd)
                CompositionLogger.Warning("Application (#{0}) cmd={1} did not set Name – using {2}".format(i, app.cmd, app.Name))

        # May already be set, but call in case not
        self.SetAppDirectories(self.Applications)

        # Don't overwrite original composition; Anticipate that SubWorkflows (Runner=None) will be using the same directory
        if (self.Runner is not None) and (os.path.exists(self.Directory)):
            CompositionLogger.RaiseError(FileExistsError, "Trying to create to a directory that already exists: {0}".format(self.Directory))

        # Create Directories
        if not os.path.exists(self.Directory):
            os.makedirs(self.Directory)
        CompositionLogger.Info("Created: {0}".format(self.Directory))
        for app in self.Applications:
            if not os.path.exists(app.Directory):
                os.makedirs(app.Directory)

        # Copy the input files
        InputCopy(self)
        for app in self.Applications:
            InputCopy(app)

        # Check for cyclic dependencies
        for app in self.Applications:
            for dep in app.DependsOn.arguments:
                depdeps = dep.DependsOn
                for depdep in depdeps.arguments:
                    if app.Name == depdep.Name:
                        CompositionLogger.RaiseError(ValueError, "Cyclic dependencies between {0} and {1}".format(app.Name, dep.Name))

        # Update the file names appropriately
        self.touchname =  os.path.join(self.Directory, "{0}.{1}".format(self.Name, self.touchname))
        self.backupname = os.path.join(self.Directory, "{0}.{1}".format(self.Name, self.backupname))
        self.submitname = os.path.join(self.Directory, "{0}.{1}".format(self.Name, self.submitname))
        self.picklename = os.path.join(self.Directory, "{0}.{1}".format(self.Name, self.picklename))

        self._CreateCalled_ = True

        # Dump pickle file when Python closes
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

            #cmd = ["python3", scriptname, jsonname, "--checkdest"]
            cmd = ["effis-globus-backup", self.backupname]
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


    def Submit(self, wait=True):

        if not self._CreateCalled_:
            self.Create()

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
            if not wait:
                self.__dict__['Wait'] = wait

            if "Wait" not in self.__dict__:
                self.__dict__['Wait'] = True

            if self.Wait:
                self.SubSubmit()
            else:
                tid = threading.Thread(target=self.SubSubmit)
                CompositionLogger.Info("Starting thread to run worklow")
                tid.start()
                return tid


    def SubSubmit(self):

        while True:

            for app in self.Applications:

                blocked = False
                for dep in app.DependsOn.arguments:
                    if ('Status' not in dep.__dict__) or (dep.Status is None):
                        blocked = True
                        break

                if blocked:
                    continue
                elif ('Status' in app.__dict__):
                    continue

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

                    app.__dict__['procid'] = p

            done = True
            for app in self.Applications:
                if ('procid' in app.__dict__) and ('Status' not in app.__dict__):
                    app.__dict__['Status'] = app.procid.poll()
                elif ('procid' in app.__dict__) and (app.Status is None):
                    app.__dict__['Status'] = app.procid.poll()

                if 'Status' not in app.__dict__:
                    done = False
                elif app.Status is None:
                    done = False

            if done:
                break


        with Chdir(self.Directory):
            with open(self.touchname, "w") as outfile:
                outfile.write("")


class SubWorkflow(Workflow):

    # Various workflow files
    touchname = "sub.workflow.done"     # Signals workflow finished, can run backup
    backupname = "sub.backup.json"      # Configures the globus movement
    submitname = "sub.workflow.sh"      # File that submits with scheduler
    picklename = "sub.workflow.pickle"  # Saves workflow description

    # Allow user to not wait for SubWorkflow to finish
    Wait = True


    def __init__(self, **kwargs):

        if 'Runner' in kwargs:
            CompositionLogger.RaiseError(ValueError, "SubWorkflow attribute: Runner is not supported allowed")
        kwargs['Runner'] = None
        super().__init__(**kwargs)

