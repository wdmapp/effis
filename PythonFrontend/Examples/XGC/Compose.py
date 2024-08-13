#!/usr/bin/env python3

import effis.composition
import argparse
import getpass
import datetime
import shutil
import os
import re


parser = argparse.ArgumentParser()

parser.add_argument("-i", "--inputdir", required=True, type=str, help="Path to directory with XGC input", )
parser.add_argument("-r", "--rundir",   required=True, type=str, help="Path to top parent directory for run directory", )
parser.add_argument("-x", "--xgc",      required=True, type=str, help="Path to XGC binary", )

parser.add_argument("-w", "--where",  type=str, default="perlmutter", help="Machine running on", )
parser.add_argument("-c", "--charge", type=str, default="m499",       help="Account to charge", )
parser.add_argument("-s", "--setup",  type=str, default=None,         help="Setup script", )

args = parser.parse_args()


if args.where == "perlmutter":
    w = effis.composition.Workflow(Name=os.path.basename(args.rundir.rstrip("/")), Charge=args.charge, Machine=args.where)
    RanksPerNode = 4
    CoresPerRank = 32
    w.SchedulerDirectives += "--constraint=gpu"
    cfgdir = "/global/homes/e/esuchyta/software/src/XGC-Devel/quickstart/inputs"
    adioscfg = os.path.join(cfgdir, "adios2cfg.xml")
    petsccfg = os.path.join(cfgdir, "petsc.rc")

    """
    Ranks = 48
    nphi = 8
    steps = 1000
    w.SchedulerDirectives += "--qos=regular"
    w.Walltime = datetime.timedelta(hours=4)
    """

    Ranks = 12
    nphi = 4
    steps = 100
    w.SchedulerDirectives += "--qos=debug"
    w.Walltime = datetime.timedelta(minutes=30)

w.ParentDirectory = os.path.dirname(args.rundir)
xgc = effis.composition.Application(Filepath=args.xgc, Name="XGC", Ranks=Ranks, RanksPerNode=RanksPerNode, CoresPerRank=CoresPerRank, GPUsPerRank=1)

if not os.path.exists(args.inputdir):
    raise FileNotFoundError("--inputdir={0} does not exist".format(args.inputdir))
for filename in os.listdir(args.inputdir):
    xgc.Input += effis.composition.Input(os.path.join(args.inputdir, filename))
for filename in [adioscfg, petsccfg]:
    xgc.Input += effis.composition.Input(filename)

if (args.setup is not None) and os.path.exists(args.setup):
    xgc.SetupFile = args.setup

w += xgc
w.Create()


inputfile = os.path.join(xgc.Directory, "input")
if not os.path.exists(inputfile):
    shutil.copy("{0}_xgc1".format(inputfile), inputfile)

# Edit the number of poloidal planes, number of steps
with open(inputfile, "r") as infile:
    intxt = infile.read()
pattern = re.compile("^\s*sml_nphi_total\s*=\s*\d+", re.MULTILINE)
intxt = pattern.sub("sml_nphi_total={0}".format(nphi), intxt)
pattern = re.compile("^\s*sml_mstep\s*=\s*\d+", re.MULTILINE)
intxt = pattern.sub("sml_mstep={0}".format(steps), intxt)
pattern = re.compile("^\s*diag_1d_period\s*=\s*\d+", re.MULTILINE)
intxt = pattern.sub("diag_1d_period={0}".format(1), intxt)
with open(inputfile, "w") as infile:
    infile.write(intxt)


print("Created:", w.WorkflowDirectory)
print("Run job with:", os.path.join(w.WorkflowDirectory, getpass.getuser(), "run-all.sh"))

