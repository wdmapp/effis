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
import yaml
import getpass
import omas

from effis.composition.runner import Detected, UseRunner
from effis.composition.application import Application, DependsClass
from effis.composition.arguments import Arguments
from effis.composition.input import InputList
from effis.composition.backup import Backup
from effis.composition.campaign import Campaign
from effis.composition.log import CompositionLogger

"""
try:
    import adios2
except:
    adios2 = None
"""


class Chdir(ContextDecorator):
    """
    Context manager that works with Python's with statement -- changes directory and then returns
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


def FindExt(path, files=[], ext=".bp", isdir=True):
    if path is None:
        path = "./"
    paths = os.listdir(path)
    for p in paths:
        fullpath = os.path.join(path, p)
        if os.path.isdir(fullpath):
            if isdir and fullpath.endswith(ext):
                files += [fullpath]
            else:
                FindExt(path=fullpath, files=files, ext=ext, isdir=isdir)
        elif fullpath.endswith(ext):
            files += [fullpath]

    return files


def FindBP(path=None):
    '''
    if path is None:
        path = "./"
    paths = os.listdir(path)
    for p in paths:
        fullpath = os.path.join(path, p)
        if os.path.isdir(fullpath):
            if fullpath.endswith(".bp"):
                bp += [fullpath]
            else:
                FindBP(path=fullpath, bp=bp)
    '''
    bp = FindExt(path, ext=".bp", isdir=True)
    return bp



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

    #: Lets set a max running for the group
    GroupMax = {}

    #: ADIOS Campaign Management – Use campaign other than Directory name
    Campaign = None

    #: Workflow-Workflow dependencies
    DependsOn = []

    # Use MPI MPMD; not supported yet
    MPMD = False

    # Appends the current time to the created workflow directory (Might get rid of this)
    TimeIndex = False


    # Various workflow files
    _touchname_ = "workflow.done"     # Signals workflow finished, can run backup
    _backupname_ = "backup.json"      # Configures the globus movement
    _submitname_ = "workflow.sh"      # File that submits with scheduler
    _picklename_ = "workflow.pickle"  # Saves workflow description

    # Used with checking for the Runner
    _RunnerError_ = (CompositionLogger.Warning, "No batch queue [Workflow] Runner found, conintuining without one.")

    # Used to make sure Create() is called before Submit()
    _CreateCalled_ = False

    
    def setattr(self, name, value):
        """
        Attribute setting; due to inheritance, names are guaranteed to be in the class
        """

        # Throw errors for bad attribute type settings
        if (name in ("Name", "Directory", "SetupFile")) and (value is not None) and (type(value) is not str):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a string".format(name))
        elif name in ("Subdirs", "MPMD", "TimeIndex") and (type(value) is not bool):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a boolean".format(name))
        elif (name == "GroupMax") and (not isinstance(value, dict)):
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} should be set as a dictionary".format(name))

        # These are for Object types, will throw errors within if necessary
        if name == "SchedulerDirectives":
            super(UseRunner, self).__setattr__(name, Arguments(value))
        elif name == "Input":
            super(UseRunner, self).__setattr__(name, InputList(value))
        elif name == "Backup":
            super(UseRunner, self).__setattr__(name, Backup(value))
        elif name == "Applications":
            super(UseRunner, self).__setattr__(name, Application.CheckApplications(value))
        elif name == "Campaign":
            super(UseRunner, self).__setattr__(name, Campaign(value))
        elif (name == "DependsOn"):
            super(UseRunner, self).__setattr__(name, DependsClass(value, Workflow))

        # Check for some other conditions that don't make sense; don't set anything
        elif (name == "MPMD") and value:
            CompositionLogger.RaiseError(ValueError, "Workflow attribute: {0} is not supported yet".format(name))
        elif (name == "Subdirs") and value and self.MPMD:
            CompositionLogger.Warning("Cannot set subdirs=True because MPMD=True")

        # Will set verbatim self.<name> = value 
        else:

            if (name == "MPMD") and value and self.Subdirs:
                CompositionLogger.Info("Setting Subdirs=False because it is required with MPMD=True")
                super(UseRunner, self).__setattr__("Subdirs", False)

            if (name in ("Subdir", "MPMD")) and (len(self.Applications) > 0):
                CompositionLogger.Warning("Changing Subdir or MPMD after Application(s) have been added to a Workflow can break referencing Directory before Create()")
            elif (name == "Directory") and (self.Directory is not None):
                CompositionLogger.Warning("Changing Directory after it's been set can break referencing Directory before Create()")

            super(UseRunner, self).__setattr__(name, value)

            if (name == "Directory") and (self.Directory is not None):
                self.SetWorkflowDirectory()


    def __iadd__(self, other):
        """
        Meant as an intuitive way to build the workflow by adding applications; takes single applications or lists:
            workflow += application 
            workflow += [app1, app2]
        """

        if isinstance(other, Application) or (type(other) is list):
            self.Applications = self.Applications + other

            if self.Directory is not None:
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
            if self.Runner is None:
                thisrunner = None
                #CompositionLogger.Info("Application ({0}): Using detected runner {1}".format(UseRunner.kwargsmsg(kwargs), thisrunner.cmd))
            else:
                thisrunner = Application.DetectRunnerInfo(useprint=False)
                CompositionLogger.Info("Application ({0}): Using detected runner {1}".format(UseRunner.kwargsmsg(kwargs), thisrunner.cmd))
            kwargs['Runner'] = thisrunner
        self += Application(**kwargs)
        return self.Applications[-1]


    def GetCall(self, runnerdeps=[]):
        RunnerArgs = []
        if self.Runner is not None:
            RunnerArgs = self.Runner.GetCall(self, self.SchedulerDirectives)
            RunnerArgs += self.Runner.Dependency(runnerdeps)
            RunnerArgs += [self._submitname_]
        return RunnerArgs


    def SetWorkflowDirectory(self):
        if self.TimeIndex:
            super(UseRunner, self).__setattr__("Directory", "{0}.{1}".format(self.Directory, datetime.datetime.now().strftime('%Y-%m-%d.%H.%M.%S')))
        super(UseRunner, self).__setattr__("Directory", os.path.abspath(self.Directory))


    def SetAppDirectories(self, applications):
        for app in applications:
            super(UseRunner, app).__setattr__("Directory", self.Directory)
            if self.Subdirs and (app.Name is not None):
                super(UseRunner, app).__setattr__("Directory", os.path.join(app.Directory, app.Name))
    

    def PickleWrite(self):
        """
        Write the workflow to a pickle file
        """

        with open(os.path.join(self.Directory, self._picklename_), 'wb') as handle:
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
                CompositionLogger.Warning("Workflow Name={3} Application (#{0}) cmd={1} did not set Name -- using {2}".format(i, app.cmd, app.Name, self.Name))

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
                    #if app.Name == depdep.Name:
                    if app is depdep:
                        CompositionLogger.RaiseError(ValueError, "Cyclic dependencies between {0} and {1}".format(app.Name, dep.Name))

        # Update the file names appropriately
        super(UseRunner, self).__setattr__("_touchname_", os.path.join(self.Directory, "{0}.{1}".format(self.Name, self._touchname_)))
        super(UseRunner, self).__setattr__("_backupname_", os.path.join(self.Directory, "{0}.{1}".format(self.Name, self._backupname_)))
        super(UseRunner, self).__setattr__("_submitname_", os.path.join(self.Directory, "{0}.{1}".format(self.Name, self._submitname_)))
        super(UseRunner, self).__setattr__("_picklename_", os.path.join(self.Directory, "{0}.{1}".format(self.Name, self._picklename_)))

        """
        if adios2 is not None:
            bpname = "Workflow-{0}.bp".format(self.Name)
            super(UseRunner, self).__setattr__('Stream', adios2.Stream(os.path.join(self.Directory, bpname), "w"))
            self.Stream.write("user", getpass.getuser())
            self.Stream.write("CreateTime", str(datetime.datetime.now()))
            self.Stream.close()
        """

        super(UseRunner, self).__setattr__("_CreateCalled_", True)

        # Dump pickle file when Python closes
        atexit.register(self.PickleWrite)


    def SetupBackup(self):

        if len(self.Backup.destinations) > 0:

            if self.Backup.source is None:
                self.Backup.SetSourceEndpoint()

            self.BackupDict = {
                'readyfile': self._touchname_,
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
                        #entrydict[key] = entry.__dict__[key]
                        entrydict[key] = getattr(entry, key)
                    self.BackupDict['endpoints'][endpoint]['paths'] += [entrydict]

            with open(self._backupname_, "w") as outfile:
                json.dump(self.BackupDict, outfile, ensure_ascii=False, indent=4)


    def SubmitBackup(self):

        if len(self.Backup.destinations) > 0:

            #cmd = ["python3", scriptname, jsonname, "--checkdest"]
            cmd = ["effis-globus-backup", self._backupname_]
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


    def Campaignify(self):

        if self.Campaign.Available:

            CampaignName = self.Campaign.Name
            cdir = os.path.dirname(self.Directory)
            reldir = os.path.basename(self.Directory)

            with Chdir(cdir):

                bp = FindBP(path=reldir)

                if self.Campaign.SchemaOnly:
                    info = omas.omas_info()
                    names = info.keys()
                    newbp = []
                    for filename in bp:
                        if os.path.splitext(os.path.basename(filename))[0] in names:
                            newbp += [filename]
                    bp = newbp

                if len(bp) == 0:
                    CompositionLogger.Debug("Skipping campaign management: No .bp files")
                    return

                if not self.Campaign.ExistenceChecks():
                    return

                CompositionLogger.Info(
                    "BP files to add to campaign {0}:".format(self.Campaign.Name) + "\n" + 
                    "\n".join(bp)
                )

                with open(self.Campaign.ConfigFile, 'r') as infile:
                    config = yaml.safe_load(infile)

                storepath = os.path.join(os.path.expanduser(config['Campaign']['campaignstorepath']), "{0}.aca".format(self.Campaign.Name))
                if os.path.exists(storepath):
                    subcmd = "update"
                else:
                    subcmd = "create"

                args = [subcmd, self.Campaign.Name, "--files"] + bp

                fullcmd = [self.Campaign.ManagerCommand] + args
                CompositionLogger.Info("Campaign management: {0}".format(' '.join(fullcmd)))
                subprocess.call(fullcmd)


    def While(self, condition):
        if CompositionLogger.ERROR:
            #CompositionLogger.RaiseError("Workflow Name={0} exiting because of global error".format(self.Name))
            CompositionLogger.Info("Workflow Name={0} exiting because of global error".format(self.Name))
            sys.exit()
        else:
            return condition


    def GetID(self, dep, idstr, start, BackgroundTimeout=0, ids=None, names=None, current=datetime.datetime.now()):

        while self.While(
            (
                (current - start).total_seconds() < BackgroundTimeout
                or
                BackgroundTimeout == -1
            )
            and
            (
                idstr not in dep.__dir__()
            )
        ):
            current = datetime.datetime.now()

        if idstr not in dep.__dir__():
            CompositionLogger.RaiseError(
                ValueError,
                "Waiting for Dependency Name={0} of Workflow Name={1} timed out".format(
                    dep.Name,
                    self.Name
                )
            )

        elif getattr(dep, idstr) is None:
            CompositionLogger.RaiseError(
                ValueError,
                "Cannot determine {2} for Workflow Name={0} to make it a depedency for Workflow Name={1}".format(
                    dep.Name,
                    self.Name,
                    idstr,
                )
            )

        if ids is not None:
            ids += [getattr(dep, idstr)]
        if names is not None:
            names += [dep.Name]

        return getattr(dep, idstr), dep.Name


    def GetDependencies(self, BackgroundTimeout=0):

        # Check for cyclic dependencies, which don't make sense
        for dep in self.DependsOn.arguments:
            for depdep in dep.DependsOn.arguments:
                if depdep is self:
                    CompositionLogger.RaiseError(
                        ValueError,
                        "Cyclic Workflow depencies between {0} and {1}".format(
                            self.Name,
                            dep.Name
                        )
                    )

        runnerdeps = []
        runnernames = []
        threaddeps = []
        threadnames = []

        start = datetime.datetime.now()
        current = start

        for dep in self.DependsOn.arguments:

            if dep.Runner is not None:
                jobid, name = self.GetID(dep, "JobID", start, BackgroundTimeout=BackgroundTimeout, ids=runnerdeps, names=runnernames)
            else:
                threadid, name = self.GetID(dep, "tid", start, BackgroundTimeout=BackgroundTimeout, ids=threaddeps, names=threadnames)

        return runnerdeps, runnernames, threaddeps, threadnames


    def ThreadWait(self, threaddeps, threadnames):

        if len(threaddeps) > 0:

            CompositionLogger.Info(
                "Workflow Name={0} must wait for Runner=None Workflows Name={1} to finish before submitting".format(
                    self.Name,
                    ','.join(threadnames)
                )
            )

            alive = [True]*len(threaddeps)
            while self.While(any(alive)):
                for i, tid in enumerate(threaddeps):
                    alive[i] = tid.is_alive()


    def RunnerSubmit(self, SubmitCall, threaddeps=[], threadnames=[]):
        self.ThreadWait(threaddeps, threadnames)
        CompositionLogger.Info("Calling: {0}".format(" ".join(SubmitCall)))
        result = subprocess.run(SubmitCall, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if 'GetJobID' in self.Runner.__dir__():
            super(UseRunner, self).__setattr__('JobID', self.Runner.GetJobID(result))
            CompositionLogger.Info("Submitted as Job ID: {0}".format(self.JobID))
        else:
            super(UseRunner, self).__setattr__('JobID', None)


    def Submit(self, wait=True, BackgroundTimeout=0):
        if BackgroundTimeout == 0:
            return self._Submit(wait=wait, BackgroundTimeout=BackgroundTimeout)
        else:
            tid = threading.Thread(
                target=self._Submit,
                kwargs={'wait': wait, 'BackgroundTimeout': BackgroundTimeout}
            )
            tid.start()
            return tid


    def _Submit(self, wait=True, BackgroundTimeout=0):
        if not self._CreateCalled_:
            self.Create()

        with Chdir(self.Directory):
            if os.path.exists(self._touchname_):
                os.remove(self._touchname_)

        self.SetupBackup()
        self.SubmitBackup()

        runnerdeps, runnernames, threaddeps, threadnames = self.GetDependencies(BackgroundTimeout=BackgroundTimeout)
        super(UseRunner, self).__setattr__('Wait', wait)

        if self.Runner is not None:
            SubmitCall = self.GetCall(runnerdeps=runnerdeps)
            with open(self._submitname_, 'w') as outfile:
                outfile.write("#!/bin/sh" + "\n")
                outfile.write("effis-submit --sub {0} --name {1}".format(self.Directory, self.Name))

            if len(threaddeps) > 0:
                tid = threading.Thread(
                    target=self.RunnerSubmit,
                    args=(SubmitCall, ),
                    kwargs={'threaddeps': threaddeps, 'threadnames': threadnames}
                )
                return self.ThreadRun(tid)
            else:
                self.RunnerSubmit(SubmitCall)

        else:

            if len(runnerdeps) > 0:
                CompositionLogger.RaiseError(
                    ValueError,
                    "Runner=None Workflow={0} depends on Queued jobs: {1}. This isn't implemented yet.".format(
                        self.Name,
                        ",".join(runnernames)
                    )
                )
            self.ThreadWait(threaddeps, threadnames)
            tid = threading.Thread(target=self.SubSubmit)
            return self.ThreadRun(tid)

        '''
        if adios2 is not None:
            self.Stream.write("LastTime", str(datetime.datetime.now()))
            self.Stream.close()
        '''

        self.PickleWrite()


    def ThreadRun(self, tid):

        tid.start()
        super(UseRunner, self).__setattr__("tid", tid)
        if self.Wait:
            self.tid.join()

        return self.tid


    def SubSubmit(self):

        GroupRunning = {}
        for app in self.Applications:
            if (app.Group is None) or (app.Group in GroupRunning):
                continue
            GroupRunning[app.Group] = []


        while self.While(True):

            for app in self.Applications:

                blocked = False
                for dep in app.DependsOn.arguments:
                    if ('Status' not in dep.__dir__()) or (dep.Status is None):
                        blocked = True
                        break
                if (app.Group is not None) and (len(GroupRunning[app.Group]) >= self.GroupMax[app.Group]):
                    blocked = True

                if blocked:
                    continue
                elif ('Status' in app.__dir__()):
                    continue

                with Chdir(app.Directory):

                    cmd = app.GetCall()
                    msg = "Running: {0}".format(" ".join(cmd))

                    if app.LogFile is not None:
                        super(UseRunner, app).__setattr__('stdout', open(app.LogFile, 'w'))
                        msg = msg + " > {0} 2>&1".format(app.LogFile)
                    else:
                        super(UseRunner, app).__setattr__('stdout', None)

                    CompositionLogger.Info(msg)

                    if app.SetupFile is not None:
                        jobfile = "./{0}.sh".format(app.Name)
                        with open(jobfile, "w") as outfile:
                            outfile.write("#!/bin/sh" + "\n")
                            outfile.write(". ./{0}".format(app.SetupFile) + "\n")
                            outfile.write("{0}".format(" ".join(cmd)))
                        os.chmod(
                            jobfile,
                            stat.S_IRUSR | stat.S_IXUSR | stat.S_IWUSR |
                            stat.S_IRGRP | stat.S_IXGRP |
                            stat.S_IROTH | stat.S_IXOTH
                        )
                        p = subprocess.Popen([jobfile], stdout=app.stdout, stderr=app.stdout, env={**os.environ, **app.Environment})
                    else:
                        p = subprocess.Popen(cmd, stdout=app.stdout, stderr=app.stdout, env={**os.environ, **app.Environment})

                    super(UseRunner, app).__setattr__('procid', p)
                    if app.Group is not None:
                        GroupRunning[app.Group] += [app.procid]

            done = True
            for app in self.Applications:
                if ('procid' in app.__dir__()) and (('Status' not in app.__dir__()) or (app.Status is None)):
                    super(UseRunner, app).__setattr__('Status', app.procid.poll())

                if ('Status' not in app.__dir__()) or (app.Status is None):
                    done = False
                elif (app.Group is not None) and (app.procid in GroupRunning[app.Group]):
                    GroupRunning[app.Group].remove(app.procid)

            if done:
                break

        for app in self.Applications:
            with Chdir(app.Directory):
                if app.stdout is not None:
                    app.stdout.close()

        with Chdir(self.Directory):
            with open(self._touchname_, "w") as outfile:
                outfile.write("")

        if self.Wait:
            self.Campaignify()


class SubWorkflow(Workflow):

    # Various workflow files
    _touchname_ = "sub.workflow.done"     # Signals workflow finished, can run backup
    _backupname_ = "sub.backup.json"      # Configures the globus movement
    _submitname_ = "sub.workflow.sh"      # File that submits with scheduler
    _picklename_ = "sub.workflow.pickle"  # Saves workflow description


    def __init__(self, **kwargs):

        if 'Runner' in kwargs:
            CompositionLogger.RaiseError(ValueError, "SubWorkflow attribute: Runner is not supported allowed")
        kwargs['Runner'] = None
        super().__init__(**kwargs)

