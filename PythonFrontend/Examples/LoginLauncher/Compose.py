#!/usr/bin/env python3

import effis.composition
import logging
import os
import datetime

effis.composition.log.CompositionLogger.SetLevel(logging.DEBUG)
LauncherExample = os.path.join(effis.composition.ExamplesPath, "LoginLauncher", "TestApp.py")
SleepExample = os.path.join(effis.composition.ExamplesPath, "NodeShare-Hostname-Sleep", "HostnameSleep.py")

where = "perlmutter"

if where == "crusher":
    w = effis.composition.Workflow(Name="Runner-12", Charge="csc143", Machine="frontier", TimeIndex=False)
    w.SchedulerDirectives += "--core-spec=0"
    w.SchedulerDirectives += "--time=00:08:00"
    w.SchedulerDirectives += "--qos=debug"

if where == "summit":
    w = effis.composition.Workflow(Name="Summit-01", Charge="fus161", Machine="summit", TimeIndex=False)
    w.Walltime = datetime.timedelta(minutes=8)
    w.Queue = "debug"
    w.ParentDirectory = "/gpfs/alpine2/world-shared/fus161/esuchyta/effis/T3D"

elif where == "perlmutter":
    #w = effis.composition.Workflow(Name="LoginApp-05", Charge="m4564",  TimeIndex=False, Machine="perlmutter_cpu", Node=effis.composition.Node(cores=128, gpus=0))
    w = effis.composition.Workflow(Name="LoginApp-15", Charge="m4564",  TimeIndex=False, Machine="perlmutter_cpu")
    w.SchedulerDirectives += "--constraint=cpu"
    w.SchedulerDirectives += "--time=00:05:00"
    w.ParentDirectory = "/pscratch/sd/e/esuchyta/testing"
    
    '''
    #w.Queue = "shared_milan_ss11"
    w.SchedulerDirectives += "--qos=shared"
    w.SchedulerDirectives += "--ntasks=2"
    w.SchedulerDirectives += "--cpus-per-task=2"
    '''

App1 = effis.composition.LoginNodeApplication(Filepath=LauncherExample, Name="Launcher", UseNodes=2)
App1.Input += effis.composition.Input("TestFile01.txt")
App1.CommandLineArguments += "--nothing=Testing"

"""
App2 = effis.composition.Application(Filepath=SleepExample, Ranks=1, RanksPerNode=1, CoresPerRank=56, GPUsPerRank=0, Name="ComputeNode")
App2.CommandLineArguments += "--SleepTime=60"
App2.Input += effis.composition.Input("TestFile01.txt")
"""

w += App1
#w += App1 + App2
w.Create()

print(w.Directory, w.Applications[0].Directory)

