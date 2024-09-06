#!/usr/bin/env python3


import argparse
import datetime
import shutil
import os
import json
import sys
import xml.etree.ElementTree as ET
import effis.composition


parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
parser.add_argument("--analysis", help="Run analysis", action="store_true")
parser.add_argument("--plot", help="Run plotter", action="store_true")
parser.add_argument("--stream", help="Stream instead of file", action="store_true")
parser.add_argument("-b", "--backup", help="Backup run to other location; format: <Globus endpoint>:directory", type=str, default=None)
args = parser.parse_args()

if (args.backup is not None) and (args.backup.find(':') == -1):
    raise ValueError("Incorrect format for --backup. Use <Globus endpoint>:directory")


runner = effis.composition.Workflow.DetectRunnerInfo()

MyWorkflow = effis.composition.Workflow(
    Runner=runner,
    ParentDirectory=os.path.dirname(args.outdir),   # - ParentDirctory: The directory to create new workflows into
    Name=os.path.basename(args.outdir.rstrip("/")), # - Name: The workflow will run and create its output in <ParentDirectory/Name>
)

Simulation = MyWorkflow.Application(
    Filepath=shutil.which("adios2_simulations_gray-scott"),     # – Filepath: The path of the executable to run
    Name="Simulation",                                          # – Name: Will run in a subdirectory set by Name
    Ranks=2,
    RanksPerNode=2,
)

Simulation.SetupFile = "/Users/ericsuchyta/Code/effis/Examples/GrayScott/Runs/test.sh"

configdir = os.path.join(os.path.dirname(Simulation.Filepath), "..", "share", "adios2", "gray-scott")
jsonfile = os.path.join(configdir, "settings-files.json")

Simulation.Input += effis.composition.Input(jsonfile, rename="settings.json")
Simulation.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))

Simulation.CommandLineArguments += "settings.json"


if args.analysis:

    Analysis = MyWorkflow.Application(
        Filepath=shutil.which("adios2_simulations_gray-scott_pdf-calc"),
        Name="Analysis",
        #Ranks=1,
        #RanksPerNode=1
    )
    simulation_filename = os.path.join(Simulation.Directory, "gray-scott.bp")
    analysis_filename = "pdf.bp"
    Analysis.CommandLineArguments += [simulation_filename, analysis_filename]           # Can add more than one at once
    Analysis.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))


if args.plot and args.analysis:

    PDFPlot = MyWorkflow.Application(
        Filepath=shutil.which("python3"),
        CommandLineArguments=os.path.join(configdir, "pdfplot.py"),
        Name="PDFPlot",
        Runner=None,
    )
    PDFPlot.CommandLineArguments += "--instream={0}".format(os.path.join(Analysis.Directory, analysis_filename))
    PDFPlot.Input += effis.composition.Input(os.path.join(configdir, "adios2.xml"))


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
        if args.plot:
            tree.write(os.path.join(PDFPlot.Directory, "adios2.xml"))

    else:
        Analysis.DependsOn += [Simulation]


if args.backup is not None:
    endpoint, directory = args.backup.split(':')
    MyWorkflow.Backup['Remote'] = effis.composition.Destination(endpoint)  # The destination is set with UUID of the Globus endpoint
    MyWorkflow.Backup['Remote'] += effis.composition.SendData(MyWorkflow.Directory, outpath=directory)


#MyWorkflow.NewSubmit()
