#!/usr/bin/env python3

import effis.composition
import t3d.trinity_lib

import argparse
import os
import re


if __name__ == "__main__":

    runner = effis.composition.Workflow.DetectRunnerInfo()


    parser = argparse.ArgumentParser()

    if isinstance(runner, effis.composition.runner.summit):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=3)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="2:00")
        parser.add_argument("-c", "--charge", help="charge", required=True, type=str)

    elif isinstance(runner, effis.composition.runner.perlmutter):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=4)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="02:00:00")
        parser.add_argument("-c", "--charge", help="charge", required=True, type=str)
        parser.add_argument("-q", "--qos", help="QOS", required=False, type=str, default="regular")

    parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
    args = parser.parse_args()

    extra = {}
    for key in ('nodes', 'walltime', 'charge'):
        if key in args.__dict__:
            extra[key.title()] = args.__dict__[key]
    for key in ('qos'):
        if key in args.__dict__:
            extra[key.upper()] = args.__dict__[key]

    if isinstance(runner, effis.composition.runner.perlmutter):
        extra['Constraint'] = 'gpu'


    MyWorkflow = effis.composition.Workflow(
        Runner=runner,
        Directory=args.outdir,
        **extra
    )

    configname = "test-w7x-gx"
    Simulation = MyWorkflow.Application(
        cmd="t3d",
        Name="T3D",
        Runner=None,
    )
    Simulation.CommandLineArguments += [
        "{0}.in".format(configname),
        "--log", "{0}.out".format(configname),
    ]

    t3dir = os.path.dirname(t3d.trinity_lib.__file__)
    setupdir = os.path.join(os.path.dirname(t3dir), "tests", "regression")
    datadir = os.path.join(os.path.dirname(t3dir), "tests", "data")
    Simulation.Input += effis.composition.Input(os.path.join(setupdir, "{0}.in".format(configname)))
    Simulation.Input += effis.composition.Input(os.path.join(datadir, "wout_w7x.nc"))
    Simulation.Input += effis.composition.Input(os.path.join(setupdir, "gx_template.in"))

    if isinstance(runner, effis.composition.runner.summit):
        Simulation.Environment['GX_PATH'] = "/ccs/home/esuchyta/software/build/summit/gx-adios"
        Simulation.Environment['GK_SYSTEM'] = "summit"
        Simulation.SetupFile = os.path.join(os.path.dirname(__file__), "modules-summit.sh")
    elif isinstance(runner, effis.composition.runner.perlmutter):
        Simulation.Environment['GX_PATH'] = "/global/homes/e/esuchyta/software/build/perlmutter/gx-adios-2"
        Simulation.Environment['GK_SYSTEM'] = "perlmutter"
        Simulation.SetupFile = os.path.join(os.path.dirname(__file__), "modules-perlmutter.sh")

    MyWorkflow.Create()


    # Rewrite a few things in the config file
    with open(os.path.join(Simulation.Directory, "{0}.in".format(configname)), 'r') as infile:
        config = infile.read()
    config = re.compile("geo_file\s*=\s*.*", re.MULTILINE).sub('geo_file = "wout_w7x.nc"', config)
    config = re.compile("gx_template\s*=\s*.*", re.MULTILINE).sub('gx_template = "gx_template.in"', config)
    config = re.compile("gx_outputs\s*=\s*.*", re.MULTILINE).sub('gx_outputs = "gx-flux-tubes"', config)
    with open(os.path.join(Simulation.Directory, "{0}.in".format(configname)), 'w') as outfile:
        outfile.write(config)

