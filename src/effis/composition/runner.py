import shutil
import socket
import os

from effis.composition.arguments import Arguments
from effis.composition.log import CompositionLogger


class Detected:
    """
    Keeps track of automatically detected Queue, MPI Runner info
    """
    Runner = False
    System = False


def ValidateIntOptions(options, Application, label="Application"):
    """
    Raise an error if the provided options aren't Integers (or strings of them)
    """
    for name in options:
        if (name in Application.__dir__()) and (getattr(Application, name) is not None):
            if not isinstance(getattr(Application, name), (str, int)):
                CompositionLogger.RaiseError(AttributeError, "{0} {1} setting must be an integer (or string of one)".format(name, label))
            elif not str(getattr(Application, name)).isdigit():
                CompositionLogger.RaiseError(AttributeError, "{0} {1} setting must be an integer (or string of one)".format(name, label))


class UseRunner(object):
    """
    The idea of UseRunner inheritance is an abstraction on Workflow and Application setup.
    The two are separate, but use a common backend infrastructure for attribute configuration.
    Each takes a Parallel Runner child class object (or None) to configure appropriately for the system/situation.
    """

    @classmethod
    def DetectRunnerInfo(cls, useprint=True):
        """
        Check for Batch Queue and MPI Runners on the system
        """

        if Detected.System is False:

            # Check for recognized, commonly used things
            machine = socket.getaddrinfo(socket.gethostname(), 0, flags=socket.AI_CANONNAME)[0][3].lower()


            if machine.find("perlmutter") != -1:
                Detected.System = perlmutter()
                Detected.Runner = srun()

            elif machine.find("frontier") != -1:
                Detected.System = frontier()
                Detected.Runner = srun()

            elif machine.find("andes") != -1:
                Detected.System = andes()
                Detected.Runner = srun()

            elif machine.find("summit") != -1:
                Detected.System = summit()
                #Detected.Runner = jsrun()
                Detected.Runner = srun2jsrun()

            if useprint and (Detected.System is not False):
                msg = "DetectRunnerInfo: Found {0}".format(Detected.System.__class__.__name__)
                CompositionLogger.Info(msg)


        if Detected.Runner is False:

            # Check for commands
            if shutil.which("srun") is not None:
                msg = "DetectRunnerInfo: Found Slurm"
                Detected.Runner = srun()
                if Detected.System is False:
                    Detected.System = slurm()
            elif shutil.which("mpiexec.hydra") is not None:
                msg = "DetectRunnerInfo: Found mpiexec"
                Detected.Runner = mpiexec_hydra()
                Detected.System = None
            else:
                msg = "DetectRunnerInfo: Did not find a known runner"
                Detected.Runner = None
                Detected.System = None

            if useprint:
                CompositionLogger.Info(msg)

        if 'AutoRunner' in dir(cls):
            return cls.AutoRunner()
        else:
            return Detected.System


    @staticmethod
    def kwargsmsg(kwargs):
        if "Name" in kwargs:
            return "Name = '{0}'".format(kwargs["Name"])
        else:
            return "**kwargs={0}".format(kwargs)


    def UnknownError(self, key):
        if self.Runner is None:
            rname = "None"
        else:
            rname = self.Runner.__class__.__name__
        CompositionLogger.RaiseError(AttributeError, "{0} is not an attribute for {1} using Runner={2}".format(key, self.__class__.__name__, rname))


    def __setattr__(self, name, value):

        if name not in self.__dir__():
            self.UnknownError(name)
        elif name.startswith('_') and name.endswith('_'):
            CompositionLogger.RaiseError(AttributeError, "For {1}, not allowed to explicitly set private attribute {0}".format(name, self.__class__.__name__))

        if 'setattr' in self.__dir__():
            self.setattr(name, value)
        else:
            self.__dict__[name] = value
            #super().__setattr__(name, value)


    def __init__(self, **kwargs):
        """
        Set up with the proper kind of Runner and only allow setting known attributes
        """

        if "Runner" not in kwargs:
            CompositionLogger.Warning("Runner was not set with {0} ({1}). Detecting what to use...".format(self.__class__.__name__, self.kwargsmsg(kwargs)))
            #self.__dict__['Runner'] = self.DetectRunnerInfo(useprint=False)
            super().__setattr__('Runner', self.DetectRunnerInfo(useprint=False))
            if self.Runner is None:
                self._RunnerError_[0](self._RunnerError_[1])
            else:
                CompositionLogger.Info("Using detected runner {0}".format(self.Runner.cmd))
        else:
            super().__setattr__('Runner', kwargs['Runner'])
            del kwargs['Runner']

        if self.Runner is not None:
            for key in self.Runner.options:
                super().__setattr__(key, None)


        # Set what's given in the initializer call
        for key in kwargs:
            self.__setattr__(key, kwargs[key])


        # Set the rest to the defaults,
        # including applying any special classes that are designed to handle how arguments are given as easier inputs

        for key in self.__dir__():

            if not callable(getattr(self, key)) and (key not in self.__dict__) and not (key.startswith("_") and key.endswith("_")):
                self.__setattr__(key, getattr(self, key))


class ParallelRunner:
    """
    All Batch Queues and MPI(or other multiprocess) Launchers will inherit from this.
    """ 

    cmd = None
    options = {}


    def Validate(self, Options):
        """
        Mainly calls child's Validation (ValidateOptions)
        """
        if shutil.which(self.cmd) is None:
            CompositionLogger.RaiseError(ValueError, "{0} was not found".format(self.cmd))
        if 'ValidateOptions' in self.__dir__():
            self.ValidateOptions(Options)


    def GetCall(self, Options, Extra=Arguments([])):
        """
        Get the Runner's command line call
        """
        self.Validate(Options)
        RunnerArgs = [self.cmd]

        if 'always' in self.__dir__():
            RunnerArgs += self.always

        for option in self.options:
            if getattr(Options, option) is not None:
                RunnerArgs += [self.options[option], str(getattr(Options, option))]

        for arg in Extra.arguments:
            if not isinstance(arg, str):
                RunnerArgs += [str(arg)]
            else:
                RunnerArgs += [arg]

        return RunnerArgs


class mpiexec_hydra(ParallelRunner):
    """
    mpiexec using hydra manager, which is at least by Brew MPICH
    """

    cmd = "mpiexec"
    options = {
        'Ranks': "-n",
        'RanksPerNode': "-ppn",
        'GPUsPerRank': "-gpus-per-proc",
    }


    @classmethod
    def ValidateOptions(cls, Application):
        ValidateIntOptions(cls.options, Application)
        if Application.Ranks is None:
            for name in ('RanksPerNode', 'GPUsPerRank'):
                if getattr(Application, name) is not None:
                    CompositionLogger.RaiseError(AttributeError, "Setting {0} without setting Ranks is ambiguous".format(name))
            CompositionLogger.Warning("Ranks was not set for Application name={0}. Setting it to 1 (with {1})".format(Application.Name, cls.cmd))
            Application.Ranks = 1


class lsf(ParallelRunner):
    """
    For bsub directives with a job submission
    """

    directive = "#BSUB"
    cmd = "bsub"
    options = {
        'Charge': "-P",
        'Walltime': "-W",
        'Nodes': "-nnodes",
        'Jobname': "-J",
        'Output': "-o",
        'Error': "-e",
        'alloc_flags': "-alloc_flags",
    }

    @classmethod
    def ValidateOptions(cls, Workflow):
        ValidateIntOptions(("Nodes"), Workflow, label="Workflow")
        if Workflow.Jobname is None:
            Workflow.Jobname = Workflow.Name
        if Workflow.Output is None:
            Workflow.Output = os.path.join(Workflow.Directory, "{0}-%J.out".format(Workflow.Jobname))


class summit(lsf):
    """
    Summit lsf setup
    """

    @classmethod
    def ValidateOptions(cls, Workflow):
        for name in ('Charge', 'Walltime', 'Nodes'):
            if getattr(Workflow, name) is None:
                CompositionLogger.RaiseError(AttributeError, "{0}: Summit workflow must set {1}".format(Workflow.Name, name))
        super().ValidateOptions(Workflow)


class jsrun(ParallelRunner):
    """
    For jsrun options
    """

    cmd = "jsrun"
    options = {
        'nrs': "--nrs",
        'RanksPerRs': "--tasks_per_rs",
        'CoresPerRs': "--cpu_per_rs",
        'GPUsPerRs': "--gpu_per_rs",
        'RsPerNode': "--rs_per_host",
        "bind": "--bind",
        "launch_distribution": "--launch_distribution",
    }

    @classmethod
    def ValidateOptions(cls, Application):
        ValidateIntOptions(("nrs", "RanksPerRs", "CoresPerRs", "GPUsPerRs", "RsPerNode"), Application)


class slurm(ParallelRunner):
    """
    For sbatch directives with a job submission
    """

    directive = "#SBATCH"
    cmd = "sbatch"
    options = {
        'Charge': "--account",
        'QOS': "--qos",
        'Walltime': "--time",
        'Nodes': "--nodes",
        'Constraint': "--constraint",
        'Partition': "--partition",
        'Jobname': "--job-name",
        'Output': "--output",
        'Error': "--error"
    }

    always = [
        "--parsable",
    ]

    @classmethod
    def ValidateOptions(cls, Workflow):
        ValidateIntOptions(("Nodes"), Workflow, label="Workflow")
        if Workflow.Jobname is None:
            Workflow.Jobname = Workflow.Name
        if Workflow.Output is None:
            Workflow.Output = os.path.join(Workflow.Directory, "%x-%j.out")

    @classmethod
    def GetJobID(cls, result):
        idstr = result.stdout.decode("utf-8").strip()
        return idstr

    @classmethod
    def Dependency(cls, deplist):
        deps = []
        if len(deplist) > 0:
            deps = [
                "--dependency",
                "afterok:{0}".format(":".join(deplist))
            ]
        return deps



class perlmutter(slurm):
    """
    Perlmutter sbatch setup
    """

    @classmethod
    def ValidateOptions(cls, Workflow):
        for name in ('Charge', 'Walltime', 'Nodes', 'Constraint'):
            if getattr(Workflow, name) is None:
                CompositionLogger.RaiseError(AttributeError, "{0}: Perlmutter workflow must set {1}".format(Workflow.Name, name))
        super().ValidateOptions(Workflow)


class frontier(slurm):
    """
    Frontier sbatch setup
    """

    @classmethod
    def ValidateOptions(cls, Workflow):
        for name in ('Charge', 'Walltime', 'Nodes'):
            if getattr(Workflow, name) is None:
                CompositionLogger.RaiseError(AttributeError, "{0}: Frontier workflow must set {1}".format(Workflow.Name, name))
        super().ValidateOptions(Workflow)


class andes(slurm):
    """
    Andes sbatch setup
    """

    @classmethod
    def ValidateOptions(cls, Workflow):
        for name in ('Charge', 'Walltime', 'Nodes'):
            if getattr(Workflow, name) is None:
                CompositionLogger.RaiseError(AttributeError, "{0}: Andes workflow must set {1}".format(Workflow.Name, name))
        super().ValidateOptions(Workflow)


class srun(ParallelRunner):
    """
    For srun options
    """

    cmd = "srun"
    options = {
        'Nodes': "--nodes",
        'Ranks': "--ntasks",
        'RanksPerNode': "--ntasks-per-node",
        'CoresPerRank': "--cpus-per-task",
        'GPUsPerRank': "--gpus-per-task",
        'RanksPerGPU': "--ntasks-per-gpu",
    }


    @classmethod
    def ValidateOptions(cls, Application):
        if (Application.GPUsPerRank is not None) and (Application.RanksPerGPU is not None):
            CompositionLogger.RaiseError(AttributeError, "{0}: Can only set one of GPUsPerRank and RanksPerGPU".format(Application.Name))
        ValidateIntOptions(cls.options, Application)


class srun2jsrun(srun):

    cmd = "jsrun"


    @staticmethod
    def CoresNodesAdd(RunnerArgs, Options, RanksPerRs=1, nrs=1):

        if Options.CoresPerRank is not None:
            cores_per_rs = Options.CoresPerRank * RanksPerRs
            RunnerArgs += [jsrun.options['CoresPerRs'], str(cores_per_rs)]
            RunnerArgs += [jsrun.options['bind'], "packed:{0}".format(Options.CoresPerRank)]
        else:
            CompositionLogger.Warning("Cannot determine CoresPerRs for Application Name={0}".format(Options.Name))

        if Options.RanksPerNode is not None:
            if Options.RanksPerNode % RanksPerRs != 0:
                CompositionLogger.RaiseError(AttributeError, "RanksPerNode={0} not divisible by RanksPerRs={1}".format(Options.RanksPerNode, RanksPerRs))
            rs_per_node = Options.RanksPerNode // RanksPerRs
            RunnerArgs += [jsrun.options['RsPerNode'], str(rs_per_node)]
        elif Options.Nodes is not None:
            if nrs % Options.Nodes != 0:
                CompositionLogger.RaiseError(AttributeError, "nrs={0} not divisible by Nodes={1}".format(nrs, Options.Nodes))
            rs_per_node = nrs // Options.Nodes
            RunnerArgs += [jsrun.options['RsPerNode'], str(rs_per_node)]
        elif str(Options.Ranks) == "1":
            RunnerArgs += [jsrun.options['RsPerNode'], "1"]
        else:
            CompositionLogger.Warning("Cannot determine RsPerNode for Application Name={0}".format(Options.Name))


    @classmethod
    def CallMap(cls, RunnerArgs, Options, nrs=1, GPUsPerRs=None, RanksPerRs=1):
        RunnerArgs += [jsrun.options['nrs'], str(nrs)]
        RunnerArgs += [jsrun.options['RanksPerRs'], str(RanksPerRs)]
        if GPUsPerRs is not None:
            RunnerArgs += [jsrun.options['GPUsPerRs'], str(GPUsPerRs)]
        #cls.CoresNodesAdd(RunnerArgs, Options)
        cls.CoresNodesAdd(RunnerArgs, Options, RanksPerRs=RanksPerRs, nrs=nrs)


    def GetCall(self, Options, Extra=Arguments([])):
        """
        Get the Runner's command line call
        """
        self.Validate(Options)
        RunnerArgs = [self.cmd]

        if Options.RanksPerGPU is not None:
            if Options.Ranks % Options.RanksPerGPU != 0:
                CompositionLogger.RaiseError(AttributeError, "Ranks={0} not divisible by RanksPerGPU={1}".format(Options.Ranks, Options.RanksPerGpu))
            nrs = Options.Ranks // Options.RanksPerGPU
            self.CallMap(RunnerArgs, Options, nrs=nrs, GPUsPerRs=1, RanksPerRs=Options.RanksPerGPU)

        elif Options.GPUsPerRank is not None:
            nrs = Options.Ranks
            self.CallMap(RunnerArgs, Options, nrs=nrs, GPUsPerRs=Options.GPUsPerRank, RanksPerRs=1)

        else:
            nrs = Options.Ranks
            self.CallMap(RunnerArgs, Options, nrs=nrs, RanksPerRs=1)


        for arg in Extra.arguments:
            if not isinstance(arg, str):
                RunnerArgs += [str(arg)]
            else:
                RunnerArgs += [arg]

        return RunnerArgs

