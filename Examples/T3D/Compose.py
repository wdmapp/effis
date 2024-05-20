#!/usr/bin/env python3

import effis.composition
import logging
import os
import datetime
import re

effis.composition.log.CompositionLogger.SetLevel(logging.DEBUG)

thisdir = os.path.dirname(os.path.abspath(__file__))
plotter = os.path.join(thisdir, "PlotterGX.py")

t3d_template = "test-w7x-gx.in"
gx_template = "gx_template.in"


where = "summit"

if where == "summit":
    w = effis.composition.Workflow(Name="t3d-analysis-37", Charge="fus161", Machine="summit", TimeIndex=False)
    w.Walltime = datetime.timedelta(hours=2)
    #w.Queue = "debug"

    t3d = "/ccs/home/esuchyta/.local/summit/bin/t3d"
    setup = os.path.join(thisdir, "setup.sh")
    w.ParentDirectory ="/gpfs/alpine2/world-shared/fus161/esuchyta/effis/T3D"

    #Nodes = 3
    #gpus_per_gx = 1
    Nodes = 18
    gpus_per_gx = 6
    krehm = "false"
    fields = "false"



App1 = effis.composition.LoginNodeApplication(Filepath=t3d, Name="T3D", UseNodes=Nodes)
App1.CommandLineArguments += "test-w7x-gx.in"
App1.SetupFile = setup
App1.Input += effis.composition.Input(os.path.join(thisdir, t3d_template))
App1.Input += effis.composition.Input(os.path.join(thisdir, gx_template))
App1.Input += effis.composition.Input(os.path.join(thisdir, "wout_w7x.nc"))
App1.Input += effis.composition.Input(os.path.join(thisdir, "adios2cfg.xml"))

App2 = effis.composition.LoginNodeApplication(Filepath=plotter, Name="analysis", UseNodes=0)
App2.SetupFile = setup
App2.CommandLineArguments += "--filename={0}".format(os.path.join("..", App1.Name, "Done.bp"))
App2.CommandLineArguments += "--xml={0}".format("adios2cfg.xml")
App2.Input += effis.composition.Input(os.path.join(thisdir, "adios2cfg.xml"))

w += App1
#w += App2
w.Create()

print(w.Directory)


with open(os.path.join(App1.Directory, t3d_template), "r") as infile:
    txt = infile.read()
pattern = re.compile("gpus_per_gx\s*=\s*\d+", re.MULTILINE)
txt = pattern.sub("gpus_per_gx = {0}".format(gpus_per_gx), txt)
with open(os.path.join(App1.Directory, t3d_template), "w") as outfile:
    outfile.write(txt)

with open(os.path.join(App1.Directory, gx_template), "r") as infile:
    txt = infile.read()
pattern = re.compile("krehm\s*=\s*\w+", re.MULTILINE)
txt = pattern.sub("krehm = {0}".format(krehm), txt)
pattern = re.compile("fields\s*=\s*\w+", re.MULTILINE)
txt = pattern.sub("fields = {0}".format(fields), txt)
with open(os.path.join(App1.Directory, gx_template), "w") as outfile:
    outfile.write(txt)

