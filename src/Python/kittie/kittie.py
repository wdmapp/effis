#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import adios2

import datetime
import time
import os
import copy
import numpy as np
import subprocess
import yaml
import numpy as np
import warnings


class Coupler(object):

    def __init__(self, groupname):
        self.BegunStepping = False
        self.opened = False
        self.FindStep = False
        self.groupname = groupname
        self.lockfile = False
        self.metafile = False
        self.WriteMode = False
        self.SimStep = np.empty(1, dtype=np.int32)


    def UntilNonexistentRead(self, verify=3):
        redo = False
        exists = True
        while exists:
            exists = os.path.exists(self.writing)

        self.reading = Kittie.Touch(self.reading)
        for i in range(verify):
            if os.path.exists(self.writing):
                os.remove(self.reading)
                redo = True
                break
        if redo:
            self.UntilNonexistentRead(verify=verify)


    def UntilNonexistentWrite(self):
        self.writing = Kittie.Touch(self.writing)
        for name in self.AllReading:
            exists = True
            while exists:
                exists = os.path.exists(name)


    def ReleaseLock(self):
        if self.comm is not None:
            self.comm.Barrier()

        if self.rank == 0:
            if self.WriteMode:
                os.remove(self.writing)
            elif self.mode == adios2.Mode.Read:
                os.remove(self.reading)


    def WaitDataExistence(self):
        if self.metafile:
            while not os.path.exists(os.path.join(self.filename, 'md.idx')):
                continue
            while not os.path.exists(os.path.join(self.filename, 'md.0')):
                continue


    def AcquireLock(self):
        if self.rank == 0:
            if self.WriteMode:
                self.UntilNonexistentWrite()
            elif self.mode == adios2.Mode.Read:
                #while not os.path.exists(self.filename):
                #    continue
                self.UntilNonexistentRead()

        if self.comm is not None:
            self.comm.Barrier()


    def CoupleOpen(self):
        if self.mode == adios2.Mode.Read:
            self.WaitDataExistence()

        if self.lockfile:
            self.AcquireLock()

        if self.comm is not None:
            self.engine = self.io.Open(self.filename, self.mode, self.comm)
        else:
            self.engine = self.io.Open(self.filename, self.mode)

        if self.lockfile:
            self.ReleaseLock()
        self.opened = True


    def open(self, filename, mode, comm=None):

        if not self.BegunStepping:
            self.mode = mode
            if (self.mode == adios2.Mode.Write) or (self.mode == adios2.Mode.Append):
                self.WriteMode = True
            self.CurrentStep = -1
            self.comm = comm

            if self.comm is not None:
                self.rank = self.comm.Get_rank()
            else:
                self.rank = 0

            if self.io.EngineType().lower() in Kittie.FileMethods:
                self.lockfile = True
            if self.io.EngineType().lower() in Kittie.MetaMethods:
                self.metafile = True

        if not self.opened:
            if (self.groupname in Kittie.YamlEngineSettings) and ('filename' in Kittie.YamlEngineSettings[self.groupname]):
                self.filename = Kittie.YamlEngineSettings[self.groupname]['filename']
            else:
                self.filename = filename

            self.writing = self.filename + Kittie.writing
            self.reading = self.filename + Kittie.MyReading
            self.AllReading = []
            for name in Kittie.AllReading:
                self.AllReading += [self.filename + name]

            self.CoupleOpen()


    def FileSeek(self, found, step, timeout):
        CurrentStep = -1
        self.WaitDataExistence()
        self.AcquireLock()
        if not self.opened:
            if self.comm is not None:
                self.engine = self.io.Open(self.filename, self.mode, self.comm)
            else:
                self.engine = self.io.Open(self.filename, self.mode)
            self.opened = True

        while True:
            status = self.engine.BeginStep(Kittie.ReadStepMode, timeout)

            if status == adios2.StepStatus.OK:
                CurrentStep += 1
            else:
                break

            if CurrentStep == step:
                found = True
                self.CurrentStep += 1
                break

            self.engine.EndStep()

        self.ReleaseLock()
        if not found:
            self.engine.Close()
            self.opened = False
            self.io.RemoveAllVariables()
            self.io.RemoveAllAttributes()
            if not os.path.exists(self.filename + ".done"):
                status = adios2.StepStatus.NotReady

        return status, found


    #def begin_step(self, step=None, timeout=0.0):
    def begin_step(self, step=None, timeout=-1):
        found = False

        if self.WriteMode:
            if not self.opened:
                self.CoupleOpen()
            self.engine.BeginStep(adios2.StepMode.Append, timeout)
            status = adios2.StepStatus.OK

        elif self.mode == adios2.Mode.Read:
            if step is None:
                usestep = self.CurrentStep + 1
            else:
                usestep = step

            if self.lockfile:
                while not found:
                    status, found = self.FileSeek(found, usestep, timeout)
                    if (timeout > -1.0):
                        break
            else:
                if not self.opened:
                    self.CoupleOpen()

                status = self.engine.BeginStep(Kittie.ReadStepMode, timeout)

        self.BegunStepping = True
        return status


    def AddStep(self):
        if (not self.FindStep) and (self.rank == 0) and (self.groupname in Kittie.StepGroups):
            self.FindStep = True
            if self.WriteMode:
                self.io.DefineVariable("_StepNumber", Kittie.StepNumber, [], [], [])
                self.io.DefineVariable("_StepPhysical", Kittie.StepPhysical, [], [], [])

        if self.FindStep:
            if self.WriteMode:
                vNumber = self.io.InquireVariable("_StepNumber")
                vPhysical = self.io.InquireVariable("_StepPhysical")
                self.engine.Put(vNumber, Kittie.StepNumber)
                self.engine.Put(vPhysical, Kittie.StepPhysical)
            else:
                ReadNumber = self.io.InquireVariable("_StepNumber")
                if ReadNumber is not None:
                    self.engine.Get(ReadNumber, self.SimStep)
                else:
                    self.FindStep = False


    def end_step(self):
        self.AddStep()
        if self.lockfile:
            self.AcquireLock()
        self.engine.EndStep()
        if self.lockfile:
            self.ReleaseLock()
            if self.mode == adios2.Mode.Read:
                self.engine.Close()
                self.opened = False
                self.io.RemoveAllVariables()
                self.io.RemoveAllAttributes()


    def close(self):
        if self.opened:
            if self.WriteMode and self.lockfile:
                self.AcquireLock()
            self.engine.Close()
            self.opened = False
            if self.WriteMode and self.lockfile:
                self.ReleaseLock()


class Kittie(object):
    writing = ".writing"
    reading = ".reading"
    touch = False
    OldStep = False
    #appname = None
    Codename = None

    # The namespace you init into
    adios = None
    FileMethods = ["bpfile", "bp", "bp3", "hdf5"]
    MetaMethods = ["bpfile", "bp", "bp3", "bp4", "hdf5"]

    # Getting the list of all group names found in pre-processing doesn't seem to be needed
    #CompileGroups = []

    YamlEngineSettings = {}
    StepGroups = []
    AllReading = []
    Couplers = {}
    Timers = {}

    if OldStep:
        ReadStepMode = adios2.StepMode.NextAvailable
    else:
        ReadStepMode = adios2.StepMode.Read


    #######################
    """ Utility methods """
    #######################

    @classmethod
    def Touch(cls, name):
        if cls.touch:
            subprocess.call(["touch", name])
        else:
            try:
                open(name, "w").close()
            except:
                #name = os.path.relpath(os.path.realpath(name), os.getcwd())
                name = os.path.relpath(os.path.basename(name))
                open(name, "w").close()
        return name


    ##############################
    """ Initialization Related """
    ##############################

    """
    @classmethod
    def BuildYaml(cls):
        num = os.environ["KITTIE_NUM"]
        yamlfile = os.environ["KITTIE_YAML_FILE"]
        if os.path.exists(yamlfile):
            with open(yamlfile, 'r') as ystream:
                config = yaml.load(ystream, Loader=yaml.FullLoader)
            #cls.appname = config["appname"] + "-" + num
            #cls.CompileGroups = config["groups"]
    """


    @classmethod
    def GroupsYaml(cls):
        yamlfile = ".kittie-groups-" + os.environ["KITTIE_NUM"] + ".yaml"
        if os.path.exists(yamlfile):
            with open(yamlfile, 'r') as ystream:
                cls.YamlEngineSettings = yaml.load(ystream, Loader=yaml.FullLoader)
            cls.timingdir = cls.YamlEngineSettings['.timingdir']
            del cls.YamlEngineSettings['.timingdir']
            for name in cls.YamlEngineSettings:
                if cls.YamlEngineSettings[name]["AddStep"]:
                    cls.StepGroups += [name]


    @classmethod
    def CodesYaml(cls, readid=""):
        yamlfile =  ".kittie-codenames-" + os.environ["KITTIE_NUM"] + ".yaml"
        if os.path.exists(yamlfile):
            with open(yamlfile, 'r') as ystream:
                config = yaml.load(ystream, Loader=yaml.FullLoader)
            cls.Codename = config["codename"]
            cls.MyReading = cls.reading + "-" + cls.Codename + readid
            for name in config["codes"]:
                cls.AllReading += [cls.reading + "-" + name + readid]
        else:
            cls.Codename = "unknown"
            cls.MyReading = cls.reading
            cls.AllReading = [cls.MyReading]


    @classmethod
    def Initialize(cls, comm=None, xml=None, readid=""):

        # Need a communicator in both the Kittie (global space) and each group
        cls.comm = comm
        if cls.comm is not None:
            cls.rank = cls.comm.Get_rank()
            cls.comm_self = cls.comm.Split(cls.rank, cls.rank)
        else:
            cls.rank = 0
            cls.comm_self = None

        args = []
        if xml is not None:
            args += [xml]
        if cls.comm is not None:
            args += [cls.comm]
        cls.adios = adios2.ADIOS(*args)

        cls.AllStep = False
        #cls.AllStep = True
        #cls.BuildYaml()
        cls.GroupsYaml()
        cls.CodesYaml(readid=readid)

        cls.StepInit = False
        #cls.StepGroupname = cls.appname + "-step"
        cls.StepGroupname = cls.Codename + "-step"


    @classmethod
    def Finalize(cls):
        for name in cls.Couplers.keys():
            cls.Couplers[name].close()
            if (cls.rank == 0) and cls.Couplers[name].WriteMode:
                filename = cls.Couplers[name].filename + ".done"
                filename = cls.Touch(filename)

        if cls.StepInit:
            with open(cls.StepGroupname + ".done", "w") as outfile:
                outfile.write("{0}".format(Kittie.StepNumber[0]))
            cls.StepEngine.Close()



    ############################
    """ ADIOS-like statments """
    ############################

    @classmethod
    def declare_io(cls, groupname):
        cls.Couplers[groupname] = Coupler(groupname)
        cls.Couplers[groupname].io = cls.adios.DeclareIO(groupname)
        if groupname in cls.YamlEngineSettings:
            entry = cls.YamlEngineSettings[groupname]
            if 'engine' in entry:
                cls.Couplers[groupname].io.SetEngine(entry['engine'])
            if 'params' in entry:
                for key in entry['params']:
                    cls.Couplers[groupname].io.SetParameter(key, str(entry['params'][key]))
        #cls.Couplers[groupname].io = io
        return cls.Couplers[groupname].io


    @classmethod
    def open(cls, groupname, filename, mode, comm=None):
        if comm is not None:
            cls.Couplers[groupname].open(filename, mode, comm=comm)
        else:
            cls.Couplers[groupname].open(filename, mode, comm=cls.comm)
        #cls.Couplers[groupname].open(filename, mode, comm=comm)

        return cls.Couplers[groupname].engine


    @classmethod
    def write_step(cls, physical, number, comm=None):
        if cls.rank == 0:
            cls.StepPhysical = np.array([physical], dtype=np.float64)
            cls.StepNumber = np.array([number], dtype=np.int32)
            if not cls.StepInit:
                cls.StepIO = cls.declare_io(cls.StepGroupname)
                cls.Couplers[cls.StepGroupname].mode = None
                #cls.StepIO = cls.adios.DeclareIO(cls.StepGroupname)
                cls.StepIO.DefineVariable("StepNumber", cls.StepNumber, [], [], [])
                cls.StepIO.DefineVariable("StepPhysical", cls.StepPhysical, [], [], [])
                """
                cls.StepIO.SetEngine("SST")
                cls.StepIO.SetParameter("RendezvousReaderCount", "0")
                cls.StepIO.SetParameter("QueueLimit", "1")
                cls.StepIO.SetParameter("QueueFullPolicy", "Discard")
                """
                if cls.comm_self is None:
                    cls.StepEngine = cls.StepIO.Open(cls.StepGroupname + ".bp", adios2.Mode.Write)
                else:
                    cls.StepEngine = cls.StepIO.Open(cls.StepGroupname + ".bp", adios2.Mode.Write, cls.comm_self)
                cls.StepInit = True

            cls.StepEngine.BeginStep()
            vNumber = cls.StepIO.InquireVariable("StepNumber")
            vPhysical = cls.StepIO.InquireVariable("StepPhysical")
            cls.StepEngine.Put(vNumber, cls.StepNumber)
            cls.StepEngine.Put(vPhysical, cls.StepPhysical)
            cls.StepEngine.EndStep()


    @classmethod
    def start_timer(cls, name, comm=None):
        if name not in cls.Timers:
            cls.Timers[name] = {}
            firstgroup = list(cls.YamlEngineSettings.keys())[0]
            timefile = os.path.join(cls.timingdir, "{0}.bp".format(name))
            cls.Timers[name]['diff'] = np.zeros(1)

            cls.Timers[name]['io'] = cls.adios.DeclareIO(name)
            if (comm is None) and (cls.comm is not None):
                comm = cls.comm

            if comm is not None:
                from mpi4py import MPI
                cls.Wtime = MPI.Wtime
                rank = comm.Get_rank()
                size = comm.Get_size()
                cls.Timers[name]['io'].DefineVariable('time', cls.Timers[name]['diff'], [size], [rank], [1])
                cls.Timers[name]['engine'] = cls.Timers[name]['io'].Open(timefile, adios2.Mode.Write, comm)

            else:
                cls.Wtime = time.time
                cls.Timers[name]['io'].DefineVariable('time', cls.Timers[name]['diff'], [1], [0], [1])
                cls.Timers[name]['engine'] = cls.Timers[name]['io'].Open(timefile, adios2.Mode.Write)

        cls.Timers[name]['start'] = cls.Wtime()


    @classmethod
    def stop_timer(cls, name):
        if (name in cls.Timers) and ('start' in cls.Timers[name].keys()):
            if ('stop' not in cls.Timers[name].keys()) or (cls.Timers[name]['start'] > cls.Timers[name]['stop']):
                cls.Timers[name]['stop'] = cls.Wtime()
                var = cls.Timers[name]['io'].InquireVariable('time')
                cls.Timers[name]['diff'][0] = cls.Timers[name]['stop'] - cls.Timers[name]['start']
                cls.Timers[name]['engine'].BeginStep()
                cls.Timers[name]['engine'].Put(var, cls.Timers[name]['diff'])
                cls.Timers[name]['engine'].EndStep()
                cls.Timers[name]['start'] = cls.Timers[name]['stop']
            else:
                warnings.warn("Found stop without matching start for timer {0}".format(name), RuntimeWarning)

        else:
            warnings.warn("Found stop without matching start for timer {0}".format(name), RuntimeWarning)

    @classmethod
    def PlotMap(cls, plotname, groupname, directory):
        if cls.Couplers[groupname].FindStep:
            ioname = plotname + ".done"
            if ioname not in cls.Couplers:
                io = cls.declare_io(ioname)
                VarNumber = io.DefineVariable("Step", cls.Couplers[groupname].SimStep, [], [], [])
                if cls.comm is not None:
                    engine = cls.open(ioname, ioname + ".bp", adios2.Mode.Write, cls.comm_self)
                else:
                    engine = cls.open(ioname, ioname + ".bp", adios2.Mode.Write)
                
            tmp = os.path.join("{0}-images".format(plotname), "{0}".format(cls.Couplers[groupname].SimStep[0]))
            os.makedirs(tmp)
            tmp = os.path.join(tmp, "{0}-{1}".format(cls.Codename, plotname))
            os.symlink(os.path.abspath(directory), os.path.abspath(tmp))
            cls.Couplers[ioname].begin_step()
            var = cls.Couplers[ioname].io.InquireVariable("Step")
            cls.Couplers[ioname].engine.Put(var, cls.Couplers[groupname].SimStep)
            cls.Couplers[ioname].end_step();


def TimingRead(filename, comm=None):
    if comm is not None:
        adios = adios2.ADIOS(comm)
    else:
        adios = adios2.ADIOS()

    TmpIO = adios.DeclareIO("tmp-{0}".format(filename))
    TmpEngine = TmpIO.Open(filename, adios2.Mode.Read)
    steps = TmpEngine.Steps()

    data = {}
    for name in ["start", "other", "end", "total"]:
        var = TmpIO.InquireVariable(name)
        shape = var.Shape()
        var.SetSelection([[0], shape])
        var.SetStepSelection([0, steps])
        data[name] = np.zeros((steps, shape[0]))
        TmpEngine.Get(var, data[name])

    #TmpEngine.Flush()
    TmpEngine.Close()
    return data


class MovieGenerator(object):

    def __init__(self, name):
        self.name = name
        self.txtfile = ".{0}.movie.txt".format(name)
        self.txt = open(self.txtfile, "w")


    def AddFrame(self, imagepath):
        #self.txt.write("file '{0}'\n".format(imagepath))
        self.txt.write("{0}\n".format(imagepath))

