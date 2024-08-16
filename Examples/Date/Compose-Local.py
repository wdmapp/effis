#!/usr/bin/env python3

import effis.composition
import argparse
import datetime

node = effis.composition.Node(cores=4, gpus=0)

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
parser.add_argument("-n", "--runname", help="Name for the run directory", required=True, type=str)
args = parser.parse_args()

#w = effis.composition.Workflow(Name=args.runname, Charge=args.charge, Machine="perlmutter")
w = effis.composition.Workflow(Name=args.runname, Machine="local", Node=node)
w.Walltime = datetime.timedelta(minutes=5)
w.ParentDirectory = args.outdir
    
#App1 = effis.composition.Application(Filepath="/bin/date", Name="date", Ranks=2, RanksPerNode=2, CoresPerRank=1)
App1 = effis.composition.Application(Filepath="/bin/date", Name="date", Ranks=2, RanksPerNode=2)

w += App1
w.Create()

w.Backup.source = "96f84ef0-5a2c-11ef-b6d5-f55c894bd1c6"

#w.Backup['laptop'] = effis.composition.Destination("96f84ef0-5a2c-11ef-b6d5-f55c894bd1c6")
#w.Backup['laptop'] += effis.composition.SendData(w.WorkflowDirectory, outpath="/Users/ericsuchyta/Run/backup")
#w.Backup['laptop'] += effis.composition.SendData(App1.Directory, outpath="/Users/ericsuchyta/Run/backup/other")

w.Backup['nersc'] = effis.composition.Destination("9d6d994a-6d04-11e5-ba46-22000b92c6ec")
w.Backup['nersc'] += effis.composition.SendData(App1.Directory, outpath="/global/homes/e/esuchyta/tmp-02/")

w.Submit()
