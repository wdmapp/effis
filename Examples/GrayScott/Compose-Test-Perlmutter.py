#!/usr/bin/env python3

import argparse
import datetime
import shutil
import os
import json
import sys
import xml.etree.ElementTree as ET
import effis.composition


# Add command line arguments in usual Python style for easy configuration at terminal (this is orthogonal to EFFIS)
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
parser.add_argument("-c", "--charge", help="Set charge account", type=str, default="m4564")
parser.add_argument("--analysis", help="Run analysis", action="store_true")
parser.add_argument("--stream", help="Stream instead of file", action="store_true")
parser.add_argument("-b", "--backup", help="Backup run to other location; format: <Globus endpoint>:directory", type=str, default=None)
args = parser.parse_args()

if (args.backup is not None) and (args.backup.find(':') == -1):
    raise ValueError("Incorrect format for --backup. Use <Globus endpoint>:directory")


runner = effis.composition.DetectRunnerInfo(bytype=effis.composition.Workflow)

MyWorkflow = effis.composition.Workflow(
    Runner=runner,
    ParentDirectory=os.path.dirname(args.outdir),
    Name=os.path.basename(args.outdir.rstrip("/"))
)

MyWorkflow.Nodes = 1
MyWorkflow.Walltime = "00:05:00"
MyWorkflow.Charge = args.charge
MyWorkflow.Constraint = "cpu"


Simulation = MyWorkflow.Application(
    Filepath=shutil.which("adios2_simulations_gray-scott"),
    Name="Simulation",
    Ranks=2,
    RanksPerNode=2,
    CoresPerRank=1,
)
#Simulation.SetupFile = "/Users/ericsuchyta/Code/effis/Examples/GrayScott/Runs/test.sh"

configdir = os.path.join(os.path.dirname(Simulation.Filepath), "..", "share", "adios2", "gray-scott")
jsonfile = os.path.join(configdir, "settings-files.json")

Simulation.Input += effis.composition.Input(jsonfile, rename="settings.json")
Simulation.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))

Simulation.CommandLineArguments += "settings.json"


if args.analysis:

    Analysis = MyWorkflow.Application(
        Filepath=shutil.which("adios2_simulations_gray-scott_pdf-calc"),
        Name="Analysis",
        Ranks=1,
        RanksPerNode=1,
        CoresPerRank=1,
    )
    simulation_filename = os.path.join(Simulation.Directory, "gray-scott.bp")
    analysis_filename = "pdf.bp"
    Analysis.CommandLineArguments += [simulation_filename, analysis_filename]
    Analysis.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))


MyWorkflow.Create()


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

        if sys.version_info.minor >= 9:
            ET.indent(tree, space="    ", level=0)

        tree.write(os.path.join(Simulation.Directory, "adios2.xml"))
        tree.write(os.path.join(Analysis.Directory, "adios2.xml"))


if args.backup is not None:
    endpoint, directory = args.backup.split(':')
    MyWorkflow.Backup['Remote'] = effis.composition.Destination(endpoint)
    MyWorkflow.Backup['Remote'] += effis.composition.SendData(MyWorkflow.WorkflowDirectory, outpath=directory)

