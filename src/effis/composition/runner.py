import shutil
import socket
import os

from effis.composition.arguments import Arguments
from effis.composition.log import CompositionLogger


class Detected:
    Runner = False
    System = False


def ValidateIntOptions(options, Application, label="Application"):
    for name in options:
        if (name in Application.__dict__) and (Application.__dict__[name] is not None):
            if not isinstance(Application.__dict__[name], (str, int)):
                CompositionLogger.RaiseError(AttributeError, "{0} {1} setting must be an integer (or string of one)".format(name, label))
            elif not str(Application.__dict__[name]).isdigit():
                CompositionLogger.RaiseError(AttributeError, "{0} {1} setting must be an integer (or string of one)".format(name, label))


class UseRunner:

    @classmethod
    def DetectRunnerInfo(cls, useprint=True):

        if Detected.System is False:

            # Check for recognized, commonly used things
            machine = socket.getaddrinfo(socket.gethostname(), 0, flags=socket.AI_CANONNAME)[0][3].lower()
            for test in ("perlmutter", "frontier"):
                if machine.find(test) != -1:
                    Detected.System = globals()[test]()
                    Detected.Runner = srun()
                    msg = "DetectRunnerInfo: Found {0}".format(test)

                    if useprint:
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

        if 'AutoRunner' in cls.__dict__:
            return cls.AutoRunner()
        else:
            return Detected.System


    @staticmethod
    def kwargsmsg(kwargs):
        if "Name" in kwargs:
            return "Name = '{0}'".format(kwargs["Name"])
        else:
            return "**kwargs={0}".format(kwargs)


    def __init__(self, **kwargs):

        if "Runner" not in kwargs:
            CompositionLogger.Warning("Runner was not set with {0} ({1}). Detecting what to use...".format(self.__class__.__name__, self.kwargsmsg(kwargs)))
            self.__dict__['Runner'] = self.DetectRunnerInfo(useprint=False)
            if self.Runner is None:
                self._RunnerError_[0](self._RunnerError_[1])
            else:
                CompositionLogger.Info("Using detected runner {0}".format(self.Runner.cmd))
        else:
            self.__dict__['Runner'] = kwargs['Runner']
            del kwargs['Runner']

        if self.Runner is not None:
            for key in self.Runner.options:
                self.__dict__[key] = None


        for key in kwargs:
            if key not in self.__dir__():
                CompositionLogger.RaiseError(AttributeError, "{0} is not an initializer for {1} ({2}) using Runner={3}".format(key, self.__class__.__name__, self.kwargsmsg(kwargs), str(self.Runner)))
            else:
                self.__setattr__(key, kwargs[key])


        # Set the rest to the defaults in self.__dict__
        for key in self.__dir__():
            if key.startswith("__") and key.endswith("__"):
                continue
            elif callable(getattr(self, key)):
                continue
            elif key not in self.__dict__:
                self.__setattr__(key, getattr(self, key))


class ParallelRunner:
    """
    Defines a parallel runner, e.g. srun
    """ 

    cmd = None
    options = {}


    def Validate(self, Options):
        if shutil.which(self.cmd) is None:
            CompositionLogger.RaiseError(ValueError, "{0} was not found".format(self.cmd))
        if 'ValidateOptions' in self.__dir__():
            self.ValidateOptions(Options)


    def GetCall(self, Options, Extra=Arguments([])):
        self.Validate(Options)
        RunnerArgs = [self.cmd]
        for option in self.options:
            if Options.__dict__[option] is not None:
                RunnerArgs += [self.options[option], str(Options.__dict__[option])]

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
                if Application.__dict__[name] is not None:
                    CompositionLogger.RaiseError(AttributeError, "Setting {0} with setting Ranks is ambiguous".format(name))
            CompositionLogger.Warning("Ranks was not set for Application name={0}. Setting it to 1 (with {1})".format(Application.Name, cls.cmd))
            Application.Ranks = 1


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
        'Jobname': "--job-name",
        'Output': "--output",
        'Error': "--error"
    }

    @classmethod
    def ValidateOptions(cls, Workflow):
        ValidateIntOptions(("Nodes"), Workflow, label="Workflow")
        if Workflow.Jobname is None:
            Workflow.Jobname = Workflow.Name
        if Workflow.Output is None:
            Workflow.Output = os.path.join(Workflow.Directory, "%x-%j.out")



class perlmutter(slurm):
    """
    Perlmutter sbatch setup
    """

    @classmethod
    def ValidateOptions(cls, Workflow):
        for name in ('Charge', 'Walltime', 'Nodes', 'Constraint'):
            if Workflow.__dict__[name] is None:
                CompositionLogger.RaiseError(AttributeError, "{0}: Perlmutter workflow must set {1}".format(Workflow.Name, name))
        super().ValidateOptions(Workflow)


class frontier(slurm):
    """
    Frontier sbatch setup
    """

    @classmethod
    def ValidateOptions(cls, Workflow):
        for name in ('Charge', 'Walltime', 'Nodes'):
            if Workflow.__dict__[name] is None:
                CompositionLogger.RaiseError(AttributeError, "{0}: Frontier workflow must set {1}".format(Workflow.Name, name))
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

