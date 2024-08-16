# Installation

From the top directory of the repository, install using pip:
```
pip install --editable .
```


# Getting Started

Workflow composition is done using Python, setting `Workflow` and `Application` attributes.

```py 
#!/usr/bin/env python3

import effis.composition
import argparse
import datetime

# Defining the node type for Macbook
node = effis.composition.Node(cores=4, gpus=0)

# Arguments for creating my test job
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
parser.add_argument("-n", "--runname", help="Name for the run directory", required=True, type=str)
args = parser.parse_args()

# Create a workflow
w = effis.composition.Workflow(Name=args.runname, Machine="local", Node=node)
w.Walltime = datetime.timedelta(minutes=5)

# The top-level directory for the workflow data
w.ParentDirectory = args.outdir

# Configure an application
App1 = effis.composition.Application(Filepath="/bin/date", Name="date", Ranks=2, RanksPerNode=2)

# Add the application to the workflow
w += App1

# Create the workflow setup
w.Create()

# Backup data to other site
'''
w.Backup.source = "96f84ef0-5a2c-11ef-b6d5-f55c894bd1c6"
w.Backup['nersc'] = effis.composition.Destination("9d6d994a-6d04-11e5-ba46-22000b92c6ec")
w.Backup['nersc'] += effis.composition.SendData(App1.Directory, outpath="/global/homes/e/esuchyta/tmp-02/")
'''

# Submit workflow
w.Submit()
```

Running the file:
```sh
python3 Compose.py --outdir ./ --runname date-01
```