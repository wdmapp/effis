#!/usr/bin/env python3

# Start 01
# Compose.py
"""
EFFIS workflow composition is done with a Python script.
– Here we'll use an example Simulation that builds with ADIOS2 (Gray-Scott).
– Analysis and Plotting can be added
– Option to configure remote data backup
"""

import argparse
import datetime
import shutil
import os
import json
import sys
import xml.etree.ElementTree as ET


# Add command line arguments in usual Python style for easy configuration at terminal (this is orthogonal to EFFIS)
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
parser.add_argument("-m", "--machine", help="Set machine", required=False, type=str, default=None)
parser.add_argument("-c", "--charge", help="Set charge account", required=False, type=str, default=None)
parser.add_argument("--analysis", help="Run analysis", action="store_true")
parser.add_argument("--plot", help="Run plotter", action="store_true")
parser.add_argument("--stream", help="Stream instead of file", action="store_true")
parser.add_argument("-b", "--backup", help="Backup run to other location; format: <Globus endpoint>:directory", type=str, default=None)
args = parser.parse_args()

if (args.backup is not None) and (args.backup.find(':') == -1):
    raise ValueError("Incorrect format for --backup. Use <Globus endpoint>:directory")
# End 01


# Start 02
# effis.composition is the base Python module to import
import effis.composition

# Create a Workflow
MyWorkflow = effis.composition.Workflow(                    
    ParentDirectory=os.path.dirname(args.outdir),   # - ParentDirctory: The directory to create new workflows into
    Name=os.path.basename(args.outdir.rstrip("/")), # - Name: The workflow will run and create its output in <ParentDirectory/Name>
    Machine=args.machine,                           # - Machine: EFFIS will try to set automatically if nothing is set (falling back to local otherwise)
                                                    #            "local" means use mpiexec without a queue.
)
# End 02
# Start 03
''' 
Attributes can be set in the constuctor (like Name, Machine, and Node above)
or as assignments after (like ParentDirectory and Walltime below)
'''
MyWorkflow.Walltime = datetime.timedelta(minutes=5)     # - Walltime: Set walltime (not necessary for local, but will timeout after that time if set)

if args.machine == "local":
    MyWorkflow.Node = effis.composition.Node(cores=8, gpus=0)   # - Node: Won't be necessary for machines like Frontier, Perlmutter (which are already known by setting Machine).
                                                                #         If not set for "local", will detect the CPU count on the current node (no GPUs)

elif args.machine == "slurm_cluster":                               # Custom slurm cluster
    MyWorkflow.SchedulerDirectives += "--constraint=cpu"            # (I'm testing at NERSC)
    MyWorkflow.Node = effis.composition.Node(cores=128, gpus=0)     # Specify what a node is like

if args.charge is not None:
    MyWorkflow.Charge = args.charge     # Account to charge
# End 03


# Start 04
# The workflow will be made up of Applications to run. Set up the applications. Attributes can also be set on Constructor or after
Simulation = effis.composition.Application(
    Filepath=shutil.which("adios2_simulations_gray-scott"),     # – Filepath: The path of the executable to run
    Name="Simulation",                                          # – Name: Will run in a subdirectory set by Name
    Ranks=2,
    RanksPerNode=2
)

# Can use the attributes to get what's been set
configdir = os.path.join(os.path.dirname(Simulation.Filepath), "..", "share", "adios2", "gray-scott")
jsonfile = os.path.join(configdir, "settings-files.json")

# Input sets files to include with the application
Simulation.Input += effis.composition.Input(
    jsonfile,                                   # – First argument is the file to copy into Application subdirectory
    rename="settings.json",                     # – rename: Can optionally rename it
)
Simulation.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))

# Set a command line argument, here the filename we've included with the run
Simulation.CommandLineArguments += "settings.json"

# Applications are added to a Workflow object
MyWorkflow += Simulation
# End 04

# Start 05
# Commented out, as indicative if running on its own
#MyWorkflow.Create()    # Create writes the workflow setup
#MyWorkflow.Submit()    # Submit submits/runs it
# End 05


# Start 06
if args.analysis:

    Analysis = effis.composition.Application(
        Filepath=shutil.which("adios2_simulations_gray-scott_pdf-calc"),
        Name="Analysis",
        Ranks=1,
        RanksPerNode=1
    )
    simulation_filename = os.path.join(Simulation.Directory, "gray-scott.bp")
    analysis_filename = "pdf.bp"
    Analysis.CommandLineArguments += [simulation_filename, analysis_filename]           # Can add more than one at once
    Analysis.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))

    MyWorkflow += Analysis


if args.plot and args.analysis:

    PDFPlot = effis.composition.Application(
        Filepath=shutil.which("python3"),
        CommandLineArguments=os.path.join(configdir, "pdfplot.py"),
        Name="PDFPlot",
        Ranks=1,
        RanksPerNode=1
    )
    PDFPlot.CommandLineArguments += "--instream={0}".format(os.path.join(Analysis.Directory, analysis_filename))
    PDFPlot.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))

    MyWorkflow += PDFPlot


# Create writes the workflow setup
MyWorkflow.Create()


# Can edit files in usual Python ways, here updating a JSON file so input/outputs match.
# The files exist after the call to Create()
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
        for engine in root.iter('engine'):
            engine.clear()
            engine.attrib['type'] = "SST"
            engine.append(ET.Element("parameter", attrib={'key': "DataTransport", 'value': "WAN"}))
            engine.append(ET.Element("parameter", attrib={'key': "OpenTimeoutSecs", 'value': "60.0"}))
            engine.append(ET.Element("parameter", attrib={'key': "RendezvousReaderCount", 'value': "0"}))

        if sys.version_info.minor >= 9:
            ET.indent(tree, space="    ", level=0)

        tree.write(os.path.join(Simulation.Directory, "adios2.xml"))
        tree.write(os.path.join(Analysis.Directory, "adios2.xml"))
        if args.plot:
            tree.write(os.path.join(PDFPlot.Directory, "adios2.xml"))

# End 06


# Start 07
# Can backup data to other locations using Globus with Backup attribute plus Destination and SendData objects
if args.backup is not None:
    endpoint, directory = args.backup.split(':')
    MyWorkflow.Backup['Remote'] = effis.composition.Destination(endpoint)  # The destination is set with UUID of the Globus endpoint
    MyWorkflow.Backup['Remote'] += effis.composition.SendData(MyWorkflow.WorkflowDirectory, outpath=directory)


# Submit submits/runs it
MyWorkflow.Submit()
# End 07
