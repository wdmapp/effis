#!/usr/bin/env python3

import argparse
import shutil
import os
import time
import effis.composition


def SetupArgs(runner):

    fullparser = argparse.ArgumentParser()
    subparsers = fullparser.add_subparsers(help='subcommand help', dest="batchtype")
    slurmparser = subparsers.add_parser('batch', help='Go through scheduler')
    localparser = subparsers.add_parser('local', help='Run on current local node')

    if isinstance(runner, effis.composition.runner.slurm):
        slurmparser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=1)
        slurmparser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="00:05:00")
        slurmparser.add_argument("-c", "--charge", help="charge", required=True, type=str)
        if isinstance(runner, effis.composition.runner.perlmutter):
            slurmparser.add_argument("-q", "--qos", help="QOS", required=False, type=str, default="regular")
            slurmparser.add_argument("-k", "--constraint", help="cpu or gpu", required=False, type=str, default="cpu")

    for name, subparser in subparsers.choices.items():
        subparser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)

    args = fullparser.parse_args()
    return args


def Run(args, runner=None):

    if (args.batchtype == "batch") and (runner is None):
        runner = effis.composition.Workflow.DetectRunnerInfo()

    if (args.batchtype == "batch") and (runner is not None) and (not isinstance(runner, effis.composition.runner.slurm)):
        effis.composition.EffisLogger.RaiseError(ValueError, "Current batch setup is for Slurm")
    elif args.batchtype == "local":
        runner = None

    extra = {}
    for key in ('nodes', 'walltime', 'charge', 'constraint'):
        if key in args.__dict__:
            extra[key.title()] = args.__dict__[key]
    for key in ('qos'):
        if key in args.__dict__:
            extra[key.upper()] = args.__dict__[key]

    MyWorkflow = effis.composition.Workflow(
        Runner=runner,
        Directory=args.outdir,
        Subdirs=False,
        **extra,
    )
    
    Simulation = MyWorkflow.Application(
        cmd=os.path.join(os.path.abspath(os.path.dirname(__file__)), "TestApp.py"),
        Name="TestRunner",
        Runner=None,
    )
    if args.batchtype == "local":
        Simulation.CommandLineArguments += "--local"

    #MyWorkflow.Create()
    MyWorkflow.Submit()


    LocalWorkflow = effis.composition.Workflow(
        Runner=None,
        Directory=args.outdir,
        Name="Sleep",
        Subdirs=True,
    )
    sleep = LocalWorkflow.Application(
        cmd="sleep",
        Name="Sleep",
        CommandLineArguments="10",
        #Input=effis.composition.Input(__file__, outpath=5),
        #Input="5",
    )
    #sleep.Input += "5"
    #sleep.CommandLineArguments += [["10"]]
    #LocalWorkflow.Submit(wait=False)

    #sleep.Input += __file__
    #sleep.Input = "wrong"


    DepWorkflow = effis.composition.Workflow(
        Runner=runner,
        Directory="{0}-dependent".format(args.outdir),
        Subdirs=False,
        DependsOn=MyWorkflow,
        **extra,
    )
    DepWorkflow.DependsOn += LocalWorkflow
    date = DepWorkflow.Application(
        cmd="date",
        Name="Date",
        Runner=None,
    )

    did = DepWorkflow.Submit(BackgroundTimeout=-1)
    time.sleep(5)

    #LocalWorkflow.DependsOn += DepWorkflow
    LocalWorkflow.DependsOn += MyWorkflow
    lid = LocalWorkflow.Submit(wait=False)

    did.join()



if __name__ == "__main__":

    runner = effis.composition.Workflow.DetectRunnerInfo()
    args = SetupArgs(runner)
    Run(args, runner=runner)

