import os
import re
import math
import subprocess
import json
import sys

import codar.savanna
import effis.composition
import effis.composition.arguments


def GetRunner(GetCores=True, base="."):

    SweepGroupDir = os.path.join(base, "..", "..",)
    CampaignDir = os.path.join(SweepGroupDir, "..")

    envfile = os.path.join(CampaignDir, "campaign-env.sh")
    with open(envfile, "r") as infile:
        txt = infile.read()

    pattern = re.compile('\s*CODAR_WORKFLOW_RUNNER="(.*)"\s*$', re.MULTILINE)
    match = pattern.search(txt)
    rstr = match.group(1)

    runner = None
    if (rstr is None) or (rstr == "none"):
        runner = None
        raise ValueError("Haven't figured out exactly what this means yet.")
    else:
        _locals = locals()
        exec("runner = codar.savanna.runners.{0}".format(rstr), globals(), _locals)
        runner = _locals['runner']

    if GetCores:
        envfile = os.path.join(SweepGroupDir, "group-env.sh")
        with open(envfile, "r") as infile:
            txt = infile.read()
        pattern = re.compile('\s*CODAR_CHEETAH_GROUP_PROCESSES_PER_NODE="(.*)"\s*$', re.MULTILINE)
        match = pattern.search(txt)
        Cores = int(match.group(1))
        return runner, Cores
    else:
        return runner


def GetArg(arg, value):
    args = []
    if arg:
        args += [arg, "{0}".format(value)]
    return args


def GetRunnerCmd(TmpApp, runner, Cores, Nodes=None):
    nodes, cpus, gpus = GetNodes()
    
    runner_args = [runner.exe]

    if runner.exe == "srun":
        
        if TmpApp.CoresPerRank is None:
            TmpApp.CoresPerRank = Cores // TmpApp.RanksPerNode

        runner_args += [runner.nprocs_arg, "{0}".format(TmpApp.Ranks)]

        runner_args += GetArg(runner.tasks_per_node_arg, TmpApp.RanksPerNode)  # srun isn't currently using this one

        if Nodes is not None:
            runner_args += GetArg(runner.nodes_arg, Nodes)
        else:
            runner_args += GetArg(runner.nodes_arg, math.ceil(TmpApp.Ranks/TmpApp.RanksPerNode))
        
        runner_args += [runner.cpus_per_task_arg.format(TmpApp.CoresPerRank)]

        if TmpApp.RanksPerGPU is not None:
            gpunum, ranknum = TmpApp.GPUvsRank()
            runner_args += [runner.tasks_per_gpu_arg.format(ranknum)]  # This isn't exactly right, but Cheetah isn't handling the non-basic case
        elif TmpApp.GPUsPerRank is not None:
            gpunum, ranknum = TmpApp.GPUvsRank()
            runner_args += [runner.gpus_per_task_arg.format(gpunum)]  # This isn't exactly right, but Cheetah isn't handling the non-basic case


    elif runner.exe == "jsrun":

        if TmpApp.RanksPerGPU is not None:
            gpunum, ranknum = TmpApp.GPUvsRank()
        elif TmpApp.GPUsPerRank is not None:
            gpunum, ranknum = TmpApp.GPUvsRank()
        else:
            ranknum = 1
            gpunum = 0

        if (TmpApp.CoresPerRank is None) and (TmpApp.RanksPerNode is not None):
            TmpApp.CoresPerRank = cpus // TmpApp.RanksPerNode
        elif TmpApp.CoresPerRank is None:
            '''
            if (gpunum > 0) and (self.TmpApp.Ranks < gpus):
                TmpApp.CoresPerRank = cpus // gpus
            '''
            raise ValueError("Need to set at least CoresPerRank or RanksPerNode with a JobStep")

        """
        if (self.GpuNum is not None) and (self.GpuNum > 0) and (len(self.gpus) == 0):
            raise ValueError("Trying to use GPUs on SimpleRunner when then machine does not have GPUs")
        if (self.GpuNum is not None) and (self.GpuNum > 1) and (self.RankNum > 1):
            if self.GPUsPerRank is not None:
                raise ValueError("Non-integer GPUsPerRank={0} isn't really supported".format(self.GPUsPerRank))
            elif self.RanksPerGPU is not None:
                raise ValueError("Non-integer RanksPerGPU={0} isn't really supported".format(self.RanksPerGPU))

        if self.GpuNum is None:
            how = "cpus"
        else:
            c2g = self.cpus // self.gpus
            gval = c2g * self.GpuNum
            cval = self.CoresPerRank * self.RankNum
            if gval >= cval:
                how = "gpus"
            else:
                how = "cpus"
        """

        tasks_per_rs = ranknum
        gpus_per_rs = gpunum
        cores_per_rs = tasks_per_rs * TmpApp.CoresPerRank
        nrs = TmpApp.Ranks // tasks_per_rs

        total_cores = nrs * cores_per_rs
        nrs_per_host = min(Cores, total_cores) // cores_per_rs   # Possibly don't want this
            
        runner_args += [
            runner.nrs_arg, str(nrs),
            runner.tasks_per_rs_arg, str(tasks_per_rs),
            runner.cpus_per_rs_arg, str(cores_per_rs),
            runner.gpus_per_rs_arg, str(gpus_per_rs),
            runner.rs_per_host_arg, str(nrs_per_host),
            runner.launch_distribution_arg, "packed",
        ]
        
        if TmpApp.CoresPerRank > 1:
            bind_value = TmpApp.CoresPerRank
            runner_args += [runner.bind_arg, "packed:{0}".format(bind_value)]


    if isinstance(TmpApp.MPIRunnerArguments, effis.composition.arguments.Arguments):
        runner_args += TmpApp.MPIRunnerArguments.arguments

    # These are ones I'm not handling yet at the Cheetah level
    """
    if run.threads_per_core is not None:
        runner_args += [self.threads_per_core_arg.format(str(
            run.threads_per_core))]
    if run.hostfile is not None:
        runner_args += [self.hostfile, str(run.hostfile)]

    SetupFile = None  # Figure this out if I need to
    """

    runner_args += [TmpApp.Filepath]

    if isinstance(TmpApp.CommandLineArguments, effis.composition.arguments.Arguments):
        runner_args += TmpApp.CommandLineArguments.arguments

    return runner_args


def GetNodes(base="."):
    jsonfile = os.path.join(base, effis.composition.campaign.Campaign.NodeInfoFilename)
    with open(jsonfile, 'r') as infile:
        fob = json.load(infile)
    nodes = fob["UseNodes"]
    cpus = fob["cpus"]
    gpus = fob["gpus"]
    return nodes, cpus, gpus


def EffisJobStep(**kwargs):

    if ("GetLog" in kwargs) and (kwargs["GetLog"]):
        GetLog = True
        del kwargs["GetLog"]
    else:
        GetLog = False

    runner, Cores = GetRunner()

    TmpApp = effis.composition.Application(**kwargs)
    runner_args = GetRunnerCmd(TmpApp, runner, Cores)

    # Set custom environment requested by user
    restore = {}
    for var in TmpApp.Environment:
        if var in os.environ:
            restore[var] = os.environ[var]
        os.environ[var] = TmpApp.Environment[var]

    # Run here
    logname = "{0}.log".format(TmpApp.Name)
    with open(logname, 'w') as runlog:
        runlog.write(' '.join(runner_args) + "\n")
        phandle = subprocess.Popen(runner_args, stdout=runlog, stderr=runlog,)

    # Reset environment back to before
    for var in restore:
        os.environ[var] = restore[var]

    if GetLog:
        return phandle, logname
    else:
        return phandle


class EffisSimpleJobStep(effis.composition.Application):

    def __init__(self, **kwargs):
        if "log" in kwargs:
            self.log = kwargs["log"]
            del kwargs["log"]
        else:
            self.log = None

        super(EffisSimpleJobStep, self).__init__(__class__=effis.composition.Application, **kwargs)


class EffisJobRunner:

    nodes = None
    cpus = None
    gpus = None
    base = "."


    @staticmethod
    def SimpleJobStep(**kwargs):
        return EffisSimpleJobStep(**kwargs)


    def __init__(self, how="immediate", base=None):
        self.HowLaunch = how
        if self.HowLaunch not in ("immediate"):
            raise ValueError("Currently only immediately launching jobs is supported")
        if base is not None:
            self.base = base


    def JobStep(self, step):
        if not isinstance(step, EffisSimpleJobStep):
            raise ValueError("Can only add a EfisSimpleJobStep (or lists of them) to a EffisSimpleRunner")

        if self.HowLaunch == "immediate":
            if self.nodes is None:
                self.nodes, self.gpus, self.cpus = GetNodes(base=self.base)
                self.runner = GetRunner(GetCores=False, base=self.base)
            runner_args = self.GetRunnerCmd(step)
            
            # Set custom environment requested by user
            restore = {}
            for var in step.Environment:
                if var in os.environ:
                    restore[var] = os.environ[var]
                os.environ[var] = step.Environment[var]

            # Run here
            if step.log is None:
                logname = "{0}.log".format(step.Name)
                with open(logname, 'w') as runlog:
                    runlog.write(' '.join(runner_args) + "\n")
                    phandle = subprocess.Popen(runner_args, stdout=runlog, stderr=runlog)
            else:
                step.log.write(' '.join(runner_args) + "\n")
                phandle = subprocess.Popen(runner_args, stdout=step.log, stderr=step.log)

            # Reset environment back to before
            for var in restore:
                os.environ[var] = restore[var]

            if step.log is None:
                return phandle, logname
            else:
                return phandle


    def __iadd__(self, other):
        if isinstance(other, list) or isinstance(other, tuple):
            for jobstep in other:
                self.JobStep(jobstep)
        else:
            self.JobStep(other)
        return self


    def ByGpuOrCpu(self, gpunum, ranknum, CoresPerRank):
        c2g = self.cpus // self.gpus
        gval = c2g * gpunum
        cval = CoresPerRank * ranknum
        if gval >= cval:
            how = "gpus"
        else:
            how = "cpus"
        return how


    def GetRunnerCmd(self, TmpApp, Nodes=None):
        
        if TmpApp.RanksPerGPU is not None:
            gpunum, ranknum = TmpApp.GPUvsRank()
        elif TmpApp.GPUsPerRank is not None:
            gpunum, ranknum = TmpApp.GPUvsRank()
        else:
            ranknum = 1
            gpunum = 0

        if (gpunum > 0) and (self.gpus == 0):
            raise ValueError("Trying to use GPUs on SimpleRunner when then machine does not have GPUs")
        if TmpApp.Filepath is None:
            raise ValueError("Added JobStep must have a Filepath to run")

        if (TmpApp.CoresPerRank is None) and (TmpApp.RanksPerNode is None):
            raise ValueError("Need to set at least CoresPerRank or RanksPerNode with a SimpleJobStep")
        elif TmpApp.CoresPerRank is None:
            TmpApp.CoresPerRank = cpus // TmpApp.RanksPerNode

        runner_args = [self.runner.exe]


        if self.runner.exe == "srun":

            if (gpunum > 1) and (self.ranknum > 1):
                if TmpApp.GPUsPerRank is not None:
                    raise ValueError("Non-integer GPUsPerRank={0} isn't really supported in usual Slurm formatting".format(TmpApp.GPUsPerRank))
                elif TmpApp.RanksPerGPU is not None:
                    raise ValueError("Non-integer RanksPerGPU={0} isn't really supported in usual Slurm formatting".format(TmpApp.RanksPerGPU))
            
            runner_args += [self.runner.nprocs_arg, "{0}".format(TmpApp.Ranks)]

            if TmpApp.RanksPerNode is not None:
                runner_args += GetArg(self.runner.tasks_per_node_arg, TmpApp.RanksPerNode)  # srun isn't currently using this one

            if Nodes is not None:
                runner_args += GetArg(self.runner.nodes_arg, Nodes)
            elif TmpApp.RanksPerNode is not None:
                runner_args += GetArg(self.runner.nodes_arg, math.ceil(TmpApp.Ranks/TmpApp.RanksPerNode))
            else:
                how = self.ByGpuOrCpu(gpunum, ranknum, TmpApp.CoresPerRank)
                if how == "gpus":
                    runner_args += GetArg(self.runner.nodes_arg, math.ceil(TmpApp.Ranks * gpunum / self.gpus))
                elif how == "cpus":
                    runner_args += GetArg(self.runner.nodes_arg, math.ceil(TmpApp.Ranks * TmpApp.CoresPerRank / self.cpus))

            
            runner_args += [self.runner.cpus_per_task_arg.format(TmpApp.CoresPerRank)]

            if TmpApp.RanksPerGPU is not None:
                runner_args += [self.runner.tasks_per_gpu_arg.format(ranknum)]  # This isn't exactly right, but Cheetah isn't handling the non-basic case
            elif TmpApp.GPUsPerRank is not None:
                runner_args += [self.runner.gpus_per_task_arg.format(gpunum)]  # This isn't exactly right, but Cheetah isn't handling the non-basic case


        elif self.runner.exe == "jsrun":

            how = self.ByGpuOrCpu(gpunum, ranknum, TmpApp.CoresPerRank)
            if (how == "gpus"):
                gr = gpunum * TmpApp.Ranks
                if (self.gpus >= gr):
                    UsePerHost = (self.gpus % gr == 0)
                else:
                    UsePerHost = (gr % self.gpus == 0)
            else:
                cr = ranknum * TmpApp.CoresPerRank
                if (self.cpus >= cr):
                    UsePerHost = (self.cpus % cr == 0)
                else:
                    UsePerHost = (cr % self.cpus == 0)

            tasks_per_rs = ranknum
            gpus_per_rs = gpunum
            cores_per_rs = tasks_per_rs * TmpApp.CoresPerRank
            nrs = TmpApp.Ranks // tasks_per_rs
                
            runner_args += [
                self.runner.nrs_arg, str(nrs),
                self.runner.tasks_per_rs_arg, str(tasks_per_rs),
                self.runner.cpus_per_rs_arg, str(cores_per_rs),
                self.runner.gpus_per_rs_arg, str(gpus_per_rs),
                self.runner.launch_distribution_arg, "packed",
            ]

            if UsePerHost:
                total_cores = nrs * cores_per_rs
                nrs_per_host = min(self.cpus, total_cores) // cores_per_rs   # Possibly don't want this
                runner_args += [self.runner.rs_per_host_arg, str(nrs_per_host)]
            
            if TmpApp.CoresPerRank > 1:
                bind_value = TmpApp.CoresPerRank
                runner_args += [self.runner.bind_arg, "packed:{0}".format(bind_value)]


        if isinstance(TmpApp.MPIRunnerArguments, effis.composition.arguments.Arguments):
            runner_args += TmpApp.MPIRunnerArguments.arguments

        # These are ones I'm not handling yet at the Cheetah level
        """
        if run.threads_per_core is not None:
            runner_args += [self.threads_per_core_arg.format(str(
                run.threads_per_core))]
        if run.hostfile is not None:
            runner_args += [self.hostfile, str(run.hostfile)]

        SetupFile = None  # Figure this out if I need to
        """

        runner_args += [TmpApp.Filepath]

        if isinstance(TmpApp.CommandLineArguments, effis.composition.arguments.Arguments):
            runner_args += TmpApp.CommandLineArguments.arguments

        return runner_args



class SimpleJobStep(effis.composition.Application):

    #SetupFile = None
    #Environment = {}
    #ShareKey = None
    #Input = []

    def __setattr__(self, name, value):
        if name in ["MPIRunnerArguments", "Ranks", "RanksPerNode", "CoresPerRank", "GPUsPerRank", "RanksPerGPU"]:
            raise ValueError("{0} is not set by SimpleJobStep. It goes on the SimpleRunner.".format(name))
        super(SimpleJobStep, self).__setattr__(name, value)

        
    def __init__(self, **kwargs):
        self.__dict__['MPIRunnerArguments'] = effis.composition.arguments.Arguments([])
        for key in ["Ranks", "RanksPerNode", "CoresPerRank", "GPUsPerRank", "RanksPerGPU"]:
            self.__dict__[key] = None
        super(SimpleJobStep, self).__init__(__class__=effis.composition.Application, **kwargs)


class SimpleRunner(effis.composition.Application):

    def __setattr__(self, name, value):
        if name == "CommandLineArguments":
            raise ValueError("CommandLineArugments is not set by SimpleRunner. It goes on the SimpleJobSteps.")
        elif name == "Fileath":
            raise ValueError("Filepath is not set by the user with SimpleRunner. EFFIS knows what to use.")
        super(SimpleRunner, self).__setattr__(name, value)
        

    def __init__(self, **kwargs):
        self.JobSteps = []
        self.__dict__['Filepath'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "QueueRunner.py")
        self.__dict__['CommandLineArguments'] = effis.composition.arguments.Arguments([])
        super(SimpleRunner, self).__init__(__class__=effis.composition.Application, **kwargs)


    def AddJobStep(self, step):
        if not isinstance(step, SimpleJobStep):
            raise ValueError("Can only add a SimpleJobStep (or lists of them) to a SimpleRunner")
        if step.Filepath is None:
            raise ValueError("Added JobStep must have a Filepath to run")

        runner_args = [step.Filepath]
        if isinstance(step.CommandLineArguments, effis.composition.arguments.Arguments):
            runner_args += step.CommandLineArguments.arguments
        self.JobSteps += [{'cmd': runner_args, 'env': step.Environment, 'name': step.Name}]



    def __iadd__(self, other):
        if isinstance(other, list) or isinstance(other, tuple):
            for jobstep in other:
                self.AddJobStep(jobstep)
        else:
            self.AddJobStep(other)
        return self


    def GetNodes(self):
        self.nodes, self.cpus, self.gpus = GetNodes()


    def Start(self):
        if self.Name is None:
            raise ValueError("Need to set a Name with SimpleRunner.")
        if self.CoresPerRank is None:
            raise ValueError("Need to set a CoresPerRank with SimpleRunner.")

        self.CheckSensible()
        self.GpuNum, self.RankNum = self.GPUvsRank()
        self.runner = GetRunner(GetCores=False)
        self.GetNodes()

        if (self.GpuNum is not None) and (self.GpuNum > 0) and (len(self.gpus) == 0):
            raise ValueError("Trying to use GPUs on SimpleRunner when then machine does not have GPUs")
        if (self.GpuNum is not None) and (self.GpuNum > 1) and (self.RankNum > 1):
            if self.GPUsPerRank is not None:
                raise ValueError("Non-integer GPUsPerRank={0} isn't really supported".format(self.GPUsPerRank))
            elif self.RanksPerGPU is not None:
                raise ValueError("Non-integer RanksPerGPU={0} isn't really supported".format(self.RanksPerGPU))

        if self.GpuNum is None:
            how = "cpus"
        else:
            c2g = self.cpus // self.gpus
            gval = c2g * self.GpuNum
            cval = self.CoresPerRank * self.RankNum
            if gval >= cval:
                how = "gpus"
            else:
                how = "cpus"

        if how == "gpus":
            TotalGPUs = self.gpus * self.nodes
            NumGroups = TotalGPUs // (self.GpuNum * self.Ranks)
        elif how == "cpus":
            TotalCPUs = self.cpus * self.nodes
            NumGroups = TotalCPUs // (self.Ranks * self.CoresPerRank)

        self.OrigRanks = self.Ranks
        self.RanksPerNode = None
        self.Ranks *= NumGroups

        self.WriteQueue()
        
        self.__dict__['CommandLineArguments'] = effis.composition.arguments.Arguments(
            [
                "--queuefile={0}".format(self.QueueFile),
                "--setsize={0}".format(self.OrigRanks),
            ]
        )

        mainjob = self.GetRunnerCmd()
        print(' ' .join(mainjob)); sys.stdout.flush()

        self.phandle = subprocess.Popen(mainjob)
        return self.phandle


    def Wait(self):
        self.phandle.wait()


    def GetRunnerCmd(self):
        runner_args = [self.runner.exe]
        runner_args += [self.runner.nprocs_arg, "{0}".format(self.Ranks)]

        #runner_args += GetArg(self.runner.tasks_per_node_arg, self.RanksPerNode)  # srun isn't currently using this one
        runner_args += GetArg(self.runner.nodes_arg, self.nodes)
        runner_args += [self.runner.cpus_per_task_arg.format(self.CoresPerRank)]

        if self.RanksPerGPU is not None:
            gpunum, ranknum = self.GPUvsRank()
            runner_args += [self.runner.tasks_per_gpu_arg.format(ranknum)]  # This isn't exactly right, but Cheetah isn't handling the non-basic case
        elif self.GPUsPerRank is not None:
            gpunum, ranknum = self.GPUvsRank()
            runner_args += [self.runner.gpus_per_task_arg.format(gpunum)]  # This isn't exactly right, but Cheetah isn't handling the non-basic case

        if isinstance(self.MPIRunnerArguments, effis.composition.arguments.Arguments):
            runner_args += self.MPIRunnerArguments.arguments

        # These are ones I'm not handling yet at the Cheetah level
        """
        if run.threads_per_core is not None:
            runner_args += [self.threads_per_core_arg.format(str(
                run.threads_per_core))]
        if run.hostfile is not None:
            runner_args += [self.hostfile, str(run.hostfile)]

        SetupFile = None  # Figure this out if I need to
        """

        runner_args += [self.Filepath]

        if isinstance(self.CommandLineArguments, effis.composition.arguments.Arguments):
            runner_args += self.CommandLineArguments.arguments

        return runner_args



    # Consider doing this with BP
    def WriteQueue(self):
        self.QueueFile = os.path.join(".effis.queue.{0}.json".format(self.Name))
        with open(self.QueueFile, 'w', encoding='utf-8') as outfile:
            json.dump(self.JobSteps, outfile, ensure_ascii=False, indent=4)

