#!/usr/bin/env python3

import effis.composition
import argparse
import getpass
import datetime
import os

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
parser.add_argument("-n", "--runname", help="Name for the run directory", required=True, type=str)
parser.add_argument("-c", "--charge", help="Account to charge", default="m4564")
args = parser.parse_args()

w = effis.composition.Workflow(Name=args.runname, Charge=args.charge, Machine="perlmutter")
w.SchedulerDirectives += "--constraint=cpu"
w.SchedulerDirectives += "--qos=debug"
w.Walltime = datetime.timedelta(minutes=5)
#w.SchedulerDirectives += "--time=00:05:00"
w.ParentDirectory = args.outdir
    
App1 = effis.composition.Application(Filepath="/usr/bin/date", Name="date", Ranks=2, RanksPerNode=2, CoresPerRank=1)
w += App1
w.Create()

print("Created:", w.WorkflowDirectory)
print("Run job with:", os.path.join(w.WorkflowDirectory, getpass.getuser(), "run-all.sh"))
