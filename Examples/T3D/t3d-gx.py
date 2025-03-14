#!/usr/bin/env python3

import effis.composition
import t3d.trinity_lib

import argparse
import os
import re
import shutil


if __name__ == "__main__":

    # Try to automatically find what system we're on
    runner = effis.composition.Workflow.DetectRunnerInfo()


    # Add arguments to configure the composistion setup from the command line
    parser = argparse.ArgumentParser()

    if runner.__class__.__name__ in ("andes", "perlmutter", "frontier"):
        parser.add_argument("-c", "--charge", help="charge", required=True, type=str)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="02:00:00")

    if isinstance(runner, effis.composition.runner.perlmutter):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=4)
        parser.add_argument("-q", "--qos", help="QOS", type=str, default="regular")

    elif isinstance(runner, effis.composition.runner.frontier):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=2)
        parser.add_argument("-q", "--qos", help="QOS", type=str)

    elif isinstance(runner, effis.composition.runner.andes):
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=4)

    else:
        parser.add_argument("-c", "--charge", help="charge", required=False, type=str, default=None)
        parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default=None)
        parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=None)
        parser.add_argument("-q", "--qos", help="QOS", required=False, type=str, default=None)

    # --small uses 6 GX calls in parallel and only 2 time steps. (Total of 24 GX runs [2 rounds per step].)
    # Normal T3D config has 16 GX calls in parallel, with more steps [still 2 rounds of GX per step].
    parser.add_argument("--small", help="Smaller, faster run", action="store_true")

    parser.add_argument("--setupfile", help="Path to file for modules to load", type=str, default=None)
    parser.add_argument("--gk_system", help="Set GK_SYSTEM", type=str, default=None)

    parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
    args = parser.parse_args()

    extra = {}
    for key in ('nodes', 'walltime', 'charge'):
        if (key in args.__dict__) and (args.__dict__[key] is not None):
            extra[key.title()] = args.__dict__[key]
    for key in ('qos',):
        if key in args.__dict__ and (args.__dict__[key] is not None):
            extra[key.upper()] = args.__dict__[key]

    if isinstance(runner, effis.composition.runner.perlmutter):
        extra['Constraint'] = 'gpu'
    elif isinstance(runner, effis.composition.runner.andes):
        extra['Partition'] = 'gpu'


    # The "Top Level" entity to configure EFFIS is a Workflow() object
    MyWorkflow = effis.composition.Workflow(
        Runner=runner,          # Set the appropriate scheduler (e.g. Slurm)
        Directory=args.outdir,  # Where we'll run
        **extra
    )

    # Application() Objects are added to a Workflow
    Simulation = MyWorkflow.Application(
        cmd="t3d",      # The command name/path to executable
        Name="T3D",     # Label (will name run subdirectories where each app runs)
        Runner=None,    # Setting Application Runner as None means don't use the MPI Runner (T3D also internally makes srun (or equivalent) calls)
    )
    configname = "test-w7x-gx"

    # Options on an Application can also be set as attributes
    Simulation.CommandLineArguments += [
        "{0}.in".format(configname),
        "--log", "{0}.out".format(configname),
    ]

    # Input collects files to copy into an Application subdirectory (also possible to use links, rename files, etc.), which we'll edit later
    t3dir = os.path.dirname(t3d.trinity_lib.__file__)
    setupdir = os.path.join(os.path.dirname(t3dir), "tests", "regression")
    datadir = os.path.join(os.path.dirname(t3dir), "tests", "data")
    Simulation.Input += effis.composition.Input(os.path.join(setupdir, "{0}.in".format(configname)))
    geofile = "wout_w7x.nc"
    Simulation.Input += effis.composition.Input(os.path.join(datadir, geofile))
    Simulation.Input += effis.composition.Input(os.path.join(setupdir, "gx_template.in"))

    # Can set Environment variables with .Environment
    gxpath = shutil.which("gx")
    if gxpath is None:
        effis.composition.EffisLogger.RaiseError(FileExistsError, "gx not found. Add to $PATH")
    Simulation.Environment['GX_PATH'] = os.path.dirname(gxpath)

    # A SetupFile with an Application sources that file before the app runs
    if (args.setupfile is not None) and (not os.exists(args.setupfile)):
        effis.composition.EffisLogger.RaiseError(FileExistsError, "--setupfile={0} not found".format(args.setupfile))
    elif args.setupfile is not None:
        Simulation.SetupFile = args.setupfile
    elif runner.__class__.__name__ in ("andes", "perlmutter", "frontier"):
        Simulation.SetupFile = os.path.join(os.path.dirname(__file__), "modules-{0}.sh".format(runner.__class__.__name__))

    if args.gk_system is not None:
        Simulation.Environment['GK_SYSTEM'] = args.gk_system
    elif runner.__class__.__name__ in ("andes", "perlmutter", "frontier"):
        Simulation.Environment['GK_SYSTEM'] = runner.__class__.__name__


    # Run a T3D analysis plotter (that installs with T3D and would run post-hoc)
    """
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
    """

    # This runs a utility that install with EFFIS which converts NetCDF files to ADIOS files
    """
    nc2bp = MyWorkflow.Application(
        cmd="effis-nc2bp",
        Name="nc2bp",
        Runner=None,
    )
    nc2bp.CommandLineArguments += ["--directory", MyWorkflow.Directory]
    nc2bp.DependsOn += Simulation
    """

    # This is an EFFIS shim layer converter for GX, which adds schema (and saves in .bp)
    """
    gx_omas = MyWorkflow.Application(
        cmd="effis-omas-gx",
        Name="gx_omas",
        Runner=None,
    )
    gx_omas.CommandLineArguments += ["--directory", Simulation.Directory]
    gx_omas.DependsOn += Simulation
    """

    # This is an EFFIS shim layer converter for VMEC, which adds schema (and saves in .bp)
    """
    vmec_omas = MyWorkflow.Application(
        cmd="effis-omas-vmec",
        Name="vmec_omas",
        Runner=None,
        CommandLineArguments=["--filename", os.path.join(Simulation.Directory, geofile)]
    )
    """

    # Seting .Campaign adds .bp output to an ADIOS campaign
    """
    MyWorkflow.Campaign = os.path.basename(MyWorkflow.Directory)
    MyWorkflow.Campaign.SchemaOnly = True  # Only add things in the schema to the campaign file
    """

    # Create() will copy all the input to run directories
    MyWorkflow.Create()


    # Rewrite a few things in the config file; access to usual Python regex
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

