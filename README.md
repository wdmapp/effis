# Installation

```bash
pip install --editable .
```

# Getting Started

Here, let’s consider running an example simulation that installs with ADIOS (Gray-Scott),
with workflow options to turn on analysis, plotting, and remote data movement.
The code that follows below is taken from the [Compose.py](https://github.com/wdmapp/effis/blob/master/Examples/GrayScott/Compose.py)
script from `Examples/GrayScott`.

## Python Composition

Workflow composition in EFFIS is done using ordinary Python scripts.
First, this example has first just set up some command
line arguments for convenience of running.

```python
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


# Add command line arguments in usual Python style for easy configuration at terminal (this is orthogonal to EFFIS)
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
parser.add_argument("-m", "--machine", help="Set machine", required=False, type=str, default=None)
parser.add_argument("-c", "--charge", help="Set charge account", required=False, type=str, default=None)
parser.add_argument("--analysis", help="Run analysis", action="store_true")
parser.add_argument("--plot", help="Run plotter", action="store_true")
parser.add_argument("-b", "--backup", help="Backup run to other location; format: <Globus endpoint>:directory", type=str, default=None)
args = parser.parse_args()

if (args.backup is not None) and (args.backup.find(':') == -1):
    raise ValueError("Incorrect format for --backup. Use <Globus endpoint>:directory")
```

## Creating a Workflow Object

EFFIS has `effis.composition` to import, for creating a `Workflow` and
then adding `Application` objects to it. The `Workflow` and `Application`
objects have attributes to describe properties like the machine configuration,
the input files, the process decomposition, etc.

```python
# effis.composition is the base Python module to import
import effis.composition

# Create a Workflow
MyWorkflow = effis.composition.Workflow(                    
    ParentDirectory=os.path.dirname(args.outdir),   # - ParentDirctory: The directory to create new workflows into
    Name=os.path.basename(args.outdir.rstrip("/")), # - Name: The workflow will run and create its output in <ParentDirectory/Name>
    Machine=args.machine,                           # - Machine: EFFIS will try to set automatically if nothing is set (falling back to local otherwise)
                                                    #            "local" means use mpiexec without a queue.
)
```

The attributes can also be set one by after initalizing with the constuctor.

```python
''' 
Attributes can be set in the constuctor (like Name, Machine, and Node above)
or as assignments after (like ParentDirectory and Walltime below)
'''
MyWorkflow.Walltime = datetime.timedelta(minutes=5)     # - Walltime: Set walltime (not necessary for local, but will timeout after that time if set)

if args.machine == "local":
    MyWorkflow.Node = effis.composition.Node(cores=8, gpus=0)   # - Node: Won't be necessary for machines like Frontier, Perlmutter (which are already known by setting Machine).
                                                                #         If not set for "local", will detect the CPU count on the current node (no GPUs)

if args.charge is not None:
    MyWorkflow.Charge = args.charge     # Account to charge
```

## Adding Applications

Applications are set up with `Application` objets, whose configuration follows similary
to `Workflow` objects, and which are then added the `Workflow` to compose them to run.

```python
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
```

## Creating and Running the Workflow

The `Workflow` has a `Create()` method to write the directories and copy all the setups,
and then a `Submit()` method to submit it to the queue (if relevant) and run.

```python
# Commented out, as indicative if running on its own
#MyWorkflow.Create()    # Create writes the workflow setup
#MyWorkflow.Submit()    # Submit submits/runs it
```

The composition file is executed as a Python script:

```bash
python3 Compose.py --outdir GrayScott-01
```

## Adding Multiple Workflow Components

One can create multiple `Applications` objects to add to the `Workflow` to run multiple
workflow components

```python
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
```

So configuring this from the current example:

```bash
python3 Compose.py --outdir GrayScott-02 --analysis --plot
```

## Remote Data Movement/Backup

A `Workflow` has `.Backup` to add `Destination` objects, to which one can use `SendData` to call Globus to copy data to the destination.

```python
# Can backup data to other locations using Globus with Backup attribute plus Destination and SendData objects
if args.backup is not None:
    endpoint, directory = args.backup.split(':')
    MyWorkflow.Backup['Remote'] = effis.composition.Destination(endpoint)  # The destination is set with UUID of the Globus endpoint
    MyWorkflow.Backup['Remote'] += effis.composition.SendData(MyWorkflow.WorkflowDirectory, outpath=directory)


# Submit submits/runs it
MyWorkflow.Submit()
```

So configuring the current example for remote data backup to NERSC (update the directory to something approrpriate for the user):

```bash
python3 ../Compose.py --outdir GrayScott-03 --analysis --plot --backup=9d6d994a-6d04-11e5-ba46-22000b92c6ec:/global/homes/e/esuchyta/backup
```
