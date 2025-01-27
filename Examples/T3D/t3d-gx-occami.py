#!/usr/bin/env python3

import effis.composition
import t3d.trinity_lib
import occami

import argparse
import os
import re


if __name__ == "__main__":

    runner = effis.composition.Workflow.DetectRunnerInfo()


    parser = argparse.ArgumentParser()

    if isinstance(runner, effis.composition.runner.perlmutter):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=4)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="02:00:00")
        parser.add_argument("-c", "--charge", help="charge", required=True, type=str)
        parser.add_argument("-q", "--qos", help="QOS", type=str, default="regular")

    parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
    parser.add_argument("--small", help="Smaller, faster run", action="store_true")
    args = parser.parse_args()

    extra = {}
    for key in ('nodes', 'walltime', 'charge'):
        if key in args.__dict__:
            extra[key.title()] = args.__dict__[key]
    for key in ('qos',):
        if key in args.__dict__:
            extra[key.upper()] = args.__dict__[key]

    if isinstance(runner, effis.composition.runner.perlmutter):
        extra['Constraint'] = 'gpu'


    MyWorkflow = effis.composition.Workflow(
        Runner=runner,
        Directory=args.outdir,
        **extra
    )

    configname = "test-occami-gx"
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
    Simulation.Input += effis.composition.Input(os.path.join(setupdir, "gx_occami_template.in"))
    Simulation.Input += effis.composition.Input(os.path.join(setupdir, "occami"))

    if isinstance(runner, effis.composition.runner.perlmutter):
        Simulation.SetupFile = os.path.join(os.path.dirname(__file__), "modules-perlmutter.sh")
        Simulation.Environment['GK_SYSTEM'] = "perlmutter"
        Simulation.Environment['GX_PATH'] = "/global/homes/e/esuchyta/software/build/perlmutter/gx-adios-2"
        Simulation.Environment['GENRAY_APP'] = "/global/homes/e/esuchyta/software/build/perlmutter/genray/xgenray.gcc.perlmutter"


    plot = MyWorkflow.Application(
        cmd="t3d-plot",
        Name="plot",
        Runner=None,
    )
    plot.CommandLineArguments += [
        os.path.relpath(os.path.join(Simulation.Directory, "{0}.bp".format(configname)), start=plot.Directory),
        "--grid",
        "--savefig",
        "-p", "density", "temperature", "pressure", "heat_flux", "particle_flux", "flux",
    ]
    plot.DependsOn += Simulation

    #MyWorkflow.Campaign = os.path.basename(MyWorkflow.Directory)
    #MyWorkflow.Campaign = "OCCAMI"
    MyWorkflow.Create()


    # Ensure occami.py in PYTHONPATH at runtime, add PGPLOT
    with open(os.path.join(Simulation.Directory, Simulation.SetupFile), 'a') as infile:
        infile.write("\n" + "export PYTHONPATH=$PYTHONPATH:{0}".format(os.path.dirname(occami.__file__)))
        infile.write("\n" + "export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/global/homes/e/esuchyta/software/build/perlmutter/pgplot")

    # Turn on debug prints in GENRAY
    with open(os.path.join(Simulation.Directory, "occami", "input.py"), 'r') as infile:
        config = infile.read()
    config = re.compile("debug\s*=\s*.*", re.MULTILINE).sub('debug = True', config)
    with open(os.path.join(Simulation.Directory, "occami", "input.py"), 'w') as outfile:
        outfile.write(config)

    # Rewrite a few things in the config file
    with open(os.path.join(Simulation.Directory, "{0}.in".format(configname)), 'r') as infile:
        config = infile.read()
    #config = re.compile("geo_file\s*=\s*.*", re.MULTILINE).sub('geo_file = "wout_w7x.nc"', config)
    #config = re.compile("gx_template\s*=\s*.*", re.MULTILINE).sub('gx_template = "gx_template.in"', config)
    #config = re.compile("gx_outputs\s*=\s*.*", re.MULTILINE).sub('gx_outputs = "gx-flux-tubes"', config)
    #config = re.compile("\[\[model\]\]", re.MULTILINE).sub("[[model]]" + "\n" + "  " + "effis = true", config)
    config = re.compile("read_gk_coeffs\s*=\s*.*", re.MULTILINE).sub('#read_gk_coeffs = ', config)

    if args.small == True:
        config = re.compile("N_radial\s*=\s*.*", re.MULTILINE).sub('N_radial = 5', config)
        config = re.compile("N_steps\s*=\s*.*", re.MULTILINE).sub('N_steps = 10', config)
        config = re.compile("t_max\s*=\s*.*", re.MULTILINE).sub('#t_max = 10.0', config)

    with open(os.path.join(Simulation.Directory, "{0}.in".format(configname)), 'w') as outfile:
        outfile.write(config)

