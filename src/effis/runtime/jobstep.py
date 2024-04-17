import os
import re
import math
import subprocess

import codar.savanna
import effis.composition
import effis.composition.arguments


def GetArg(arg, value):
    args = []
    if arg:
        args += [arg, "{0}".format(value)]
    return args


def JobStep(**kwargs):

    SweepGroupDir = os.path.join("..", "..",)
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
        raise(ValueError, "Haven't figured out exactly what this means yet.")
    else:
        _locals = locals()
        exec("runner = codar.savanna.runners.{0}".format(rstr), globals(), _locals)
        runner = _locals['runner']
    

    envfile = os.path.join(SweepGroupDir, "group-env.sh")
    with open(envfile, "r") as infile:
        txt = infile.read()
    pattern = re.compile('\s*CODAR_CHEETAH_GROUP_PROCESSES_PER_NODE="(.*)"\s*$', re.MULTILINE)
    match = pattern.search(txt)
    Cores = int(match.group(1))
    

    TmpApp = effis.composition.Application(**kwargs)
    if TmpApp.CoresPerRank is None:
        TmpApp.CoresPerRank = TmpApp.Cores // TmpApp.RanksPerNode

    runner_args = [runner.exe]
    runner_args += [runner.nprocs_arg, "{0}".format(TmpApp.Ranks)]

    runner_args += GetArg(runner.tasks_per_node_arg, TmpApp.RanksPerNode)  # srun isn't currently using this one
    runner_args += GetArg(runner.nodes_arg, math.ceil(TmpApp.Ranks/TmpApp.RanksPerNode))
    
    runner_args += [runner.cpus_per_task_arg.format(TmpApp.CoresPerRank)]

    if TmpApp.RanksPerGPU is not None:
        gpunum, ranknum = TmpApp.GPUvsRank()
        runner_args += [runner.tasks_per_gpu_arg.format(ranknum)]  # This isn't exactly right, but Cheetah isn't handling the non-basic case
    elif TmpApp.GPUsPerRank is not None:
        gpunum, ranknum = TmpApp.GPUvsRank()
        runner_args += [runner.gpus_per_task_arg.format(gpunum)]  # This isn't exactly right, but Cheetah isn't handling the non-basic case

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

    # Set custom environment requested by user
    restore = {}
    for var in TmpApp.Environment:
        if var in os.environ:
            restore[var] = os.environ[var]
        os.environ[var] = TmpApp.Environment[var]

    # Run here
    runlog = "{0}.log".format(TmpApp.Name)
    with open(runlog, 'w') as runlog:
        runlog.write(' '.join(runner_args) + "\n")
        phandle = subprocess.Popen(runner_args, stdout=runlog, stderr=runlog,)

    # Reset environment back to before
    for var in restore:
        os.environ[var] = restore[var]

    return phandle


class SimpleRunner:

    def __init__(self):
        pass

