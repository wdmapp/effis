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

    elif isinstance(runner, effis.composition.runner.andes):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=4)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="02:00:00")
        parser.add_argument("-c", "--charge", help="charge", required=True, type=str)
        #parser.add_argument("-q", "--qos", help="QOS", type=str, default="regular")

    elif isinstance(runner, effis.composition.runner.perlmutter):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=4)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="02:00:00")
        parser.add_argument("-c", "--charge", help="charge", required=True, type=str)
        parser.add_argument("-q", "--qos", help="QOS", type=str, default="regular")

    elif isinstance(runner, effis.composition.runner.frontier):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=4)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="02:00:00")
        parser.add_argument("-c", "--charge", help="charge", required=True, type=str)
        parser.add_argument("-q", "--qos", help="QOS", type=str)

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
    elif isinstance(runner, effis.composition.runner.andes):
        extra['Partition'] = 'gpu'


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
    geofile = "wout_w7x.nc"
    Simulation.Input += effis.composition.Input(os.path.join(datadir, geofile))
    Simulation.Input += effis.composition.Input(os.path.join(setupdir, "gx_template.in"))

    if isinstance(runner, effis.composition.runner.summit):
        Simulation.Environment['GX_PATH'] = "/ccs/home/esuchyta/software/build/summit/gx-adios"
        Simulation.Environment['GK_SYSTEM'] = "summit"
        Simulation.SetupFile = os.path.join(os.path.dirname(__file__), "modules-summit.sh")
    elif isinstance(runner, effis.composition.runner.andes):
        Simulation.Environment['GX_PATH'] = "/ccs/home/esuchyta/software/build/andes/gx"
        Simulation.Environment['GK_SYSTEM'] = "andes"
        Simulation.SetupFile = os.path.join(os.path.dirname(__file__), "modules-andes.sh")
    elif isinstance(runner, effis.composition.runner.perlmutter):
        Simulation.Environment['GX_PATH'] = "/global/homes/e/esuchyta/software/build/perlmutter/gx-adios-2"
        Simulation.Environment['GK_SYSTEM'] = "perlmutter"
        Simulation.SetupFile = os.path.join(os.path.dirname(__file__), "modules-perlmutter.sh")
    elif isinstance(runner, effis.composition.runner.frontier):
        Simulation.Environment['GX_PATH'] = "/ccs/home/esuchyta/software/build/frontier/gx"
        Simulation.Environment['GK_SYSTEM'] = "frontier"
        Simulation.SetupFile = os.path.join(os.path.dirname(__file__), "modules-frontier.sh")


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

    nc2bp = MyWorkflow.Application(
        cmd="effis-nc2bp",
        Name="nc2bp",
        Runner=None,
    )
    nc2bp.CommandLineArguments += ["--directory", MyWorkflow.Directory]
    nc2bp.DependsOn += Simulation

    gx_omas = MyWorkflow.Application(
        cmd="effis-omas-gx",
        Name="gx_omas",
        Runner=None,
    )
    gx_omas.CommandLineArguments += ["--directory", Simulation.Directory]
    gx_omas.DependsOn += Simulation

    vmec_omas = MyWorkflow.Application(
        cmd="effis-omas-vmec",
        Name="vmec_omas",
        Runner=None,
        CommandLineArguments=["--filename", os.path.join(Simulation.Directory, geofile)]
    )

    MyWorkflow.Campaign = os.path.basename(MyWorkflow.Directory)
    MyWorkflow.Campaign.SchemaOnly = True
    MyWorkflow.Create()


    # Rewrite a few things in the config file
    with open(os.path.join(Simulation.Directory, "{0}.in".format(configname)), 'r') as infile:
        config = infile.read()
    config = re.compile(r"geo_file\s*=\s*.*", re.MULTILINE).sub('geo_file = "{0}"'.format(geofile), config)
    config = re.compile(r"gx_template\s*=\s*.*", re.MULTILINE).sub('gx_template = "gx_template.in"', config)
    config = re.compile(r"gx_outputs\s*=\s*.*", re.MULTILINE).sub('gx_outputs = "gx-flux-tubes"', config)

    config = re.compile(r"\[\[model\]\]", re.MULTILINE).sub("[[model]]" + 
                                                            "\n" + "  " + "effis = true" + 
                                                            "\n" + "  " + "stall_abort_count = 10" +
                                                            "\n" + "  " + "monitor_time = 30", 
                                                            config)

    if args.small == True:
        config = re.compile(r"N_radial\s*=\s*.*", re.MULTILINE).sub('N_radial = 4', config)
        config = re.compile(r"#N_steps\s*=\s*.*", re.MULTILINE).sub('N_steps = 2', config)
        config = re.compile(r"t_max\s*=\s*.*", re.MULTILINE).sub('#t_max = 10.0', config)

    with open(os.path.join(Simulation.Directory, "{0}.in".format(configname)), 'w') as outfile:
        outfile.write(config)

