#!/usr/bin/env python3

import argparse
import shutil
import os
import effis.composition

if __name__ == "__main__":

    runner = effis.composition.Workflow.DetectRunnerInfo()

    parser = argparse.ArgumentParser()

    if isinstance(runner, effis.composition.runner.perlmutter):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=1)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="00:05:00")
        parser.add_argument("-c", "--charge", help="charge", required=True, type=str)
        parser.add_argument("-q", "--qos", help="QOS", required=False, type=str, default="regular")
        parser.add_argument("-k", "--constraint", help="cpu or gpu", required=False, type=str, default="cpu")

    elif isinstance(runner, effis.composition.runner.summit):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=1)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="5")
        parser.add_argument("-c", "--charge", help="charge", required=True, type=str)

    elif runner is not None:
        raise(ValueError, "Example is configured for Perlmutter, Summit or a machine without a scheduler (using mpiexec)")

    parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
    args = parser.parse_args()

    extra = {}
    for key in ('nodes', 'walltime', 'charge', 'qos', 'constraint'):
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

    MyWorkflow.Create()
