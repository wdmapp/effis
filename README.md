# Installation

```console
pip install --editable .
```

# Getting Started

Workflow composition is done using Python, setting `Workflow` and `Application` attributes.
Here, let’s consider an example simulation (Gray-Scott), with options to

```python
#!/usr/bin/env python3

"""
EFFIS workflow composition is done with a Python script.
– Here we'll use an example Simulation that builds with ADIOS2 (Gray-Scott).
– Analysis and Plotting can be added
"""

# effis.composition is the base Python module to import
import effis.composition

import argparse
import datetime
import shutil
import os
import json


# Add command line arguments in usual Python style for easy configuration at terminal (this is orthogonal to EFFIS)
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
parser.add_argument("--analysis", help="Run analysis", action="store_true")
parser.add_argument("--plot", help="Run plotter", action="store_true")
args = parser.parse_args()


# Create a Workflow
MyWorkflow = effis.composition.Workflow(                    
    ParentDirectory=os.path.dirname(args.outdir),           # - ParentDirctory: Set the top directory where the workflow will run and create its output
    Name=os.path.basename(args.outdir.rstrip("/")),         # - Name: will set the directory name under ParentDirectory
    Machine="local",                                        # - Machine: local means use mpiexec without a queue
)
''' 
Attributes can be set in the constuctor (like Name, Machine, and Node above)
or as assignments after (like ParentDirectory and Walltime below)
'''
MyWorkflow.Walltime = datetime.timedelta(minutes=5)         # - Walltime: Set walltime (not necessary for local, but will timeout after that time if set)
MyWorkflow.Node = effis.composition.Node(cores=8, gpus=0)   # - Node: Won't be necessary for machines like Frontier, Perlmutter (which are already known by setting Machine).
                                                            #         Here it's set for my Macbook


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


if args.analysis:

    Analysis = effis.composition.Application(
        Filepath=shutil.which("adios2_simulations_gray-scott_pdf-calc"),
        Name="Analysis",
        Ranks=1,
        RanksPerNode=1
    )
    simulation_filename = os.path.join(Simulation.Directory, "gray-scott.bp")
    analysis_filename = "pdf.bp"
    Analysis.CommandLineArguments += [simulation_filename, analysis_filename]
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


if args.analysis:
    jsonfile = os.path.join(Simulation.Directory, "settings.json")
    with open(jsonfile, "r") as infile:
        config = json.load(infile)
    config["output"] = os.path.basename(simulation_filename)
    with open(jsonfile, "w") as outfile:
        json.dump(config, outfile, ensure_ascii=False, indent=4)


# Submit submits/runs it
MyWorkflow.Submit()

```

## Running the example

Simulation only:

```console
python3 ../Compose.py --outdir GrayScott-01
```

With analysis:

```console
python3 ../Compose.py --outdir GrayScott-02 --analysis
```

With analysis and plotting:

```console
python3 ../Compose.py --outdir GrayScott-02 --analysis --plot
```
