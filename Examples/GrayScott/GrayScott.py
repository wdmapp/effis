#!/usr/bin/env python3

import argparse
import datetime
import shutil
import os
import json
import sys
import xml.etree.ElementTree as ET
import effis.composition


# EFFIS Workflows and Applications use Runners, which can be automatically detected (without this call); here it's also to set up the example for different systems
runner = effis.composition.Workflow.DetectRunnerInfo()

# This is usual Python argument parsing, conceptually orthogonal to EFFIS
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
parser.add_argument("--analysis", help="Run analysis", action="store_true")
parser.add_argument("--plot", help="Run plotter", action="store_true")
parser.add_argument("--stream", help="Stream instead of file", action="store_true")
parser.add_argument("-b", "--backup", help="Backup run to other location; format: <Globus endpoint>:directory", type=str, default=None)

# Add arguments for the scheduler
if isinstance(runner, effis.composition.runner.perlmutter):
    parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=1)
    parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="00:05:00")
    parser.add_argument("-c", "--charge", help="charge", required=True, type=str)
    parser.add_argument("-q", "--qos", help="QOS", required=False, type=str, default="regular")
    parser.add_argument("-k", "--constraint", help="cpu or gpu", required=False, type=str, default="cpu")
elif isinstance(runner, effis.composition.runner.frontier):
    parser.add_argument("-n", "--nodes", help="Number of nodes", required=False, type=int, default=1)
    parser.add_argument("-w", "--walltime", help="Walltime", required=False, type=str, default="00:05:00")
    parser.add_argument("-c", "--charge", help="charge", required=True, type=str)
elif runner is not None:
    raise(ValueError, "Example is configured for Perlmutter, Frontier or a machine without a scheduler (with mpiexec)")

args = parser.parse_args()

if (args.backup is not None) and (args.backup.find(':') == -1):
    raise ValueError("Incorrect format for --backup. Use <Globus endpoint>:directory")


extra = {}
for key in ('nodes', 'walltime', 'charge', 'constraint'):
    if key in args.__dict__:
        extra[key.title()] = args.__dict__[key]
for key in ('qos'):
    if key in args.__dict__:
        extra[key.upper()] = args.__dict__[key]


# We will set up a workflow to hold Applications to run
MyWorkflow = effis.composition.Workflow(
    Runner=runner,          # If Runner wasn't given, DetectRunnerInfo() would exeucute
    Directory=args.outdir,  # - Directory: Where to run the workflow; by default, Applications will run in subdirectories
    **extra,
)

'''
# Workflow attributes can be set after the constructor as well; here, add scheduler ones if needed
if isinstance(runner, effis.composition.runner.perlmutter):
    MyWorkflow.Nodes = args.nodes
    MyWorkflow.Walltime = args.walltime
    MyWorkflow.QOS = args.qos
    MyWorkflow.Constraint = args.constraint
    MyWorkflow.Charge = args.charge
'''


# Add one more more application to a Workflow; here we'll add an example simulation from ADIOS
Simulation = MyWorkflow.Application(
    cmd=shutil.which("adios2_simulations_gray-scott"),  # – cmd: The (path of the) executable to run
    Name="Simulation",                                  # – Name: By default, will run in a subdirectory set by Name
    Ranks=2,
    RanksPerNode=2,
)

configdir = os.path.join(os.path.dirname(Simulation.cmd), "..", "share", "adios2", "gray-scott")
jsonfile = os.path.join(configdir, "settings-files.json")

# Input are files to setup the Application, which will copy into the Application's run directory
Simulation.Input += effis.composition.Input(jsonfile, rename="settings.json")
Simulation.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))

# Add command line arguments to the call
Simulation.CommandLineArguments += "settings.json"


# Add an anlysis to the workflow
if args.analysis:

    # Above, Application found the Runner by default; here, set the MPI Runner explicitly, getting an Application Runner (instead of a Workflow one for the Workflow)
    Analysis = MyWorkflow.Application(
        cmd=shutil.which("adios2_simulations_gray-scott_pdf-calc"),
        Name="Analysis",
        Ranks=1,
        RanksPerNode=1,
        Runner=effis.composition.Application.DetectRunnerInfo(),
    )
    simulation_filename = os.path.join(Simulation.Directory, "gray-scott.bp")           # Can use attributes to help set things
    analysis_filename = "pdf.bp"
    Analysis.CommandLineArguments += [simulation_filename, analysis_filename]           # Can add more than one argument at once
    Analysis.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))

    if isinstance(runner, (effis.composition.runner.perlmutter, effis.composition.runner.frontier)):
        Simulation.CoresPerRank = 1     # These are need on Perlmutter for --cpus-per-task (to imply --exact); but mpiexec.hydra doesn't have an option like this
        Analysis.CoresPerRank = 1


# Add a plotting process to the workflow
if args.plot and args.analysis:

    PDFPlot = effis.composition.Application(
        cmd=shutil.which("python3"),
        CommandLineArguments=os.path.join(configdir, "pdfplot.py"),
        Name="PDFPlot",
        Ranks=1,
        RanksPerNode=1,
    )
    # Applications can be created (outside) the Workflow, and then added in; (This will give WARNING instead of INFO if Runner is not given)
    MyWorkflow += PDFPlot

    PDFPlot.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))
    PDFPlot.CommandLineArguments += "--instream={0}".format(os.path.join(Analysis.Directory, analysis_filename))
    if isinstance(runner, (effis.composition.runner.perlmutter, effis.composition.runner.frontier)):
        PDFPlot.CommandLineArguments += "--outfile=img".format()
        PDFPlot.CoresPerRank = 1


    # We can also give Runner as None; this means that we won't use an MPI Runner, and just call the command; (Or, a Workflow runner as None would not use a batch Queue)
    ls = MyWorkflow.Application(
        cmd="ls",
        Runner=None,
    )
    ls.CommandLineArguments=["-lhrt", PDFPlot.Directory]
    ls.DependsOn = PDFPlot


# Create() will copy the input files and set up the run area
MyWorkflow.Create()


# Edit the input files for the run configuration; again, this is basically orthogonal to EFFIS, but have the ability to do Python stuff
if args.analysis:
    jsonfile = os.path.join(Simulation.Directory, "settings.json")
    with open(jsonfile, "r") as infile:
        config = json.load(infile)
    config["output"] = os.path.basename(simulation_filename)
    with open(jsonfile, "w") as outfile:
        json.dump(config, outfile, ensure_ascii=False, indent=4)

    if args.stream:
        tree = ET.parse(os.path.join(Simulation.Directory, "adios2.xml"))
        root = tree.getroot()

        for io in root.iter('io'):
            if io.attrib['name'] == "SimulationCheckpoint":
                continue

            for engine in io.iter('engine'):
                engine.clear()
                engine.attrib['type'] = "SST"
                engine.append(ET.Element("parameter", attrib={'key': "DataTransport", 'value': "WAN"}))
                engine.append(ET.Element("parameter", attrib={'key': "OpenTimeoutSecs", 'value': "60.0"}))
                engine.append(ET.Element("parameter", attrib={'key': "RendezvousReaderCount", 'value': "0"}))

        """ # Ignore this, since it's just to look prettier and requires Python >= 3.9
        if sys.version_info.minor >= 9:
            ET.indent(tree, space="    ", level=0)
        """

        tree.write(os.path.join(Simulation.Directory, "adios2.xml"))
        tree.write(os.path.join(Analysis.Directory, "adios2.xml"))
        if args.plot:
            tree.write(os.path.join(PDFPlot.Directory, "adios2.xml"))

    else:
        # Can add dependencies (which aren't necessary here, but which I'll demonstrate)
        Analysis.DependsOn += [Simulation]
        if args.plot:
            PDFPlot.DependsOn = Analysis


# Backup data to other site?
if args.backup is not None:
    endpoint, directory = args.backup.split(':')
    MyWorkflow.Backup['Remote'] = effis.composition.Destination(endpoint)  # The destination is set with UUID of the Globus endpoint
    MyWorkflow.Backup['Remote'] += effis.composition.SendData(MyWorkflow.Directory, outpath=directory)


# To submit to the queue (if relevant) and run, can use the Submit() command here; or, call effis-submit from the terminal
#MyWorkflow.Submit()


