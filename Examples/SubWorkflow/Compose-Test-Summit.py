#!/usr/bin/env python3

import argparse
import shutil
import os
import effis.composition

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
    args = parser.parse_args()

    runner = effis.composition.Workflow.DetectRunnerInfo()

    MyWorkflow = effis.composition.Workflow(
        Runner=runner,
        Directory=args.outdir,
    )
    MyWorkflow.Subdirs = False
    
    MyWorkflow.Nodes = 1
    MyWorkflow.Walltime = "5"
    MyWorkflow.Charge = "fus161"

    Simulation = MyWorkflow.Application(
        cmd="python3",
        Name="TestRunner",
        Runner=None,
    )
    Simulation.CommandLineArguments += os.path.join(os.path.dirname(os.path.join(__file__)), "TestApp.py")

    MyWorkflow.Create()
