#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function, unicode_literals

import adios2
import datetime
import os
import copy
import numpy as np
import yaml
import subprocess


class ADIOS2(object):
    adios = None
    config = None
    touch = False


def Initialize(comm=None, xml=None, appname=None):
    args = [adios2.DebugON]
    if comm is not None:
        args.insert(0, comm)
    if xml is not None:
        args.insert(0, xml)
    ADIOS2.adios = adios2.ADIOS(*args)

    if appname is not None:
        yamlfile = ".kittie-setup-{0}.yaml".format(appname)
        with open(yamlfile, 'r') as ystream:
            ADIOS2.config = yaml.load(ystream)


class Group(object):

    def _SetEngine(self, engine):

        if type(engine) is str:
            self.io.SetEngine(engine)
        elif type(engine) is dict:
            self.io.SetEngine(engine['name'])
            e = copy.copy(engine)
            del e['name']
            self.io.SetParameters(e)


    def __init__(self, groupname, engine=None):
        self.io = ADIOS2.adios.DeclareIO(groupname)

        if ADIOS2.config is not None:
            if groupname in ADIOS2.config:
                newengine = ADIOS2.config[groupname]['engine']
                if type(newengine) is not str:
                    newengine = dict(newengine)
                self._SetEngine(newengine)

        self._SetEngine(engine)


    def DefineVariable(self, name, gdims, odims, ldims, dtype):
        arr = np.empty(ldims, dtype)
        self.io.DefineVariable(name, gdims, odims, ldims, adios2.ConstantDims, arr)


class Coupler(object):

    init = False
    writing = ".writing"
    reading = ".reading"

    def UntilNonexistent(self, verify_level=3):
        redo = False
        while True:

            if self.mode == adios2.Mode.Read:
                if not os.path.lexists(self.filename):
                    continue
            rexists = os.path.lexists("{0}{1}".format(self.filename, self.reading))
            wexists = os.path.lexists("{0}{1}".format(self.filename, self.writing))

            if rexists and wexists:
                if self.mode == adios2.Mode.Read:
                    os.remove("{0}{1}".format(self.filename, self.reading))
                continue
            elif rexists or wexists:
                continue
            else:
                break

        if self.mode == adios2.Mode.Write:
            if ADIOS2.touch:
                subprocess.call(["touch", "{0}{1}".format(self.filename, self.writing)])
            else:
                open("{0}{1}".format(self.filename, self.writing), "w").close()

        elif self.mode == adios2.Mode.Read:
            if ADIOS2.touch:
                subprocess.call(["touch", "{0}{1}".format(self.filename, self.reading)])
            else:
                open("{0}{1}".format(self.filename, self.reading), "w").close()

            for v in range(verify_level):
                if os.path.lexists("{0}{1}".format(self.filename, self.writing)):
                    os.remove("{0}{1}".format(self.filename, self.reading))
                    redo = True
                    break
        if redo:
            self.UntilNonexistent(verify_level=verify_level)


    def Lock(self, action):

        if self.comm is not None:
            if action == "release":
                self.comm.Barrier()
            rank = self.comm.Get_rank()

        if (self.comm is None) or (rank == 0):
            if action == "acquire":
                self.UntilNonexistent()
            else:
                if self.mode == adios2.Mode.Write:
                    os.remove("{0}{1}".format(self.filename, self.writing))
                elif self.mode == adios2.Mode.Read:
                    os.remove("{0}{1}".format(self.filename, self.reading))

        if (self.comm is not None) and (action == 'acquire'):
            self.comm.Barrier()


    def ReleaseLock(self):
        self.Lock('release')


    def AcquireLock(self):
        self.Lock('acquire')


    @property
    def LockFile(self):
        if self.io.EngineType().lower() in ['bpfile', 'bp', 'bp3', 'hdf5']:
            return True
        else:
            return False


    def FileSeek(self, step, timeout=-1.0):
        found = False
        current_step = -1

        self.AcquireLock()
        self.engine = self.io.Open(self.filename, self.mode)

        while True:
            status = self.engine.BeginStep(adios2.StepMode.NextAvailable, timeout)
            if status == adios2.StepStatus.OK:
                current_step = current_step + 1
            else:
                break

            if current_step == step:
                found = True
                break

            self.engine.EndStep()

        self.ReleaseLock()
        if not found:
            self.engine.Close()

            self.io.RemoveAllVariables()
            self.io.RemoveAllAttributes()
            """
            self.groupname = "{0}+".format(self.groupname)
            Group(self.groupname)
            self.io = ADIOS2.adios.AtIO(self.groupname)
            """

            #self.FileSeek(step)

        return found


    def CoupleOpen(self):
        if self.LockFile:
            self.AcquireLock()
        self.engine = self.io.Open(self.filename, self.mode)
        if self.LockFile:
            self.ReleaseLock()


    """
        More or less, these are the methods to actually use in apps.
            * __init__ is like kittie_couple_start in fortran
            * The others have basically the same names
    """

    def BeginStep(self, filename=None, groupname=None, mode=None, comm=None, step=None, timefile=None, timeout=-1.0):
        if groupname is not None:
            self.groupname = groupname
            self.io = ADIOS2.adios.AtIO(self.groupname)

        if not self.init:
            self.timefile = timefile

        if self.timefile is not None:
            self.start_time = datetime.datetime.now()

        if not self.init:
            self.filename = filename
            self.comm = comm
            self.mode = mode
            #self.groupname = groupname
            #self.io = ADIOS2.adios.AtIO(self.groupname)

            if self.timefile is not None:
                self.timinggroup = "{0}-timing".format(self.groupname)

                if self.comm is not None:
                    self.rank = self.comm.Get_rank()
                    self.size = self.comm.Get_size()
                else:
                    self.rank = 0
                    self.size = 1

                self.timing_io = ADIOS2.adios.DeclareIO(self.timinggroup)
                self.timing_io.DefineVariable("start", [self.size], [self.rank], [1], adios2.ConstantDims, np.empty(1, np.float64))
                self.timing_io.DefineVariable("end", [self.size], [self.rank], [1], adios2.ConstantDims, np.empty(1, np.float64))
                self.timing_io.DefineVariable("other", [self.size], [self.rank], [1], adios2.ConstantDims, np.empty(1, np.float64))
                self.timing_engine = self.timing_io.Open(self.filename, adios2.Mode.Write)

        if self.mode == adios2.Mode.Write:
            if not self.init:
                self.CoupleOpen()
                #self.io.LockDefinitions()
            self.engine.BeginStep(adios2.StepMode.Append)
            found = True

        elif self.mode == adios2.Mode.Read:
            if self.LockFile:
                if step is None:
                    raise ValueError("If reading from file for coupling, must give what step you want to read from")

                found = False
                while not found:
                    found = self.FileSeek(step, timeout)
                    if timeout != -1:
                        break

            else:
                if not self.init:
                    self.CoupleOpen()
                found = self.engine.BeginStep(adios2.StepMode.NextAvailable, timeout)

        self.init = True

        if self.timefile is not None:
            self.start_time = (datetime.datetime.now() - self.start_time).total_seconds()
            self.other_time = datetime.datetime.now()

        return found


    def __init__(self, filename=None, groupname=None, mode=None, comm=None, step=None, timefile=None):
        self.groupname = groupname
        self.io = ADIOS2.adios.AtIO(self.groupname)


    def Put(self, varname, outdata):
        varid = self.io.InquireVariable(varname)
        self.engine.Put(varid, outdata, adios2.Mode.Deferred)


    def GetSelection(self, outdata, varname, starts, counts):
        varid = self.io.InquireVariable(varname)
        varid.SetSelection([starts, counts])
        self.engine.Get(varid, outdata, adios2.Mode.Deferred)


    def EndStep(self):
        if (self.timefile is not None) and (self.comm is not None):
            self.other_time = (datetime.datetime.now() - self.other_time).total_seconds()
            self.end_time = datetime.datetime.now()

        if self.LockFile:
            self.AcquireLock()

        self.engine.EndStep()

        if self.LockFile:
            self.ReleaseLock()
            if self.mode == adios2.Mode.Read:
                self.engine.Close()

                self.io.RemoveAllVariables()
                self.io.RemoveAllAttributes()
                """
                self.groupname = "{0}+".format(self.groupname)
                Group(self.groupname)
                self.io = ADIOS2.adios.AtIO(self.groupname)
                """

        if (self.timefile is not None) and (self.comm is not None):
            self.end_time = (datetime.datetime.now() - self.end_time).total_seconds()
            self.timing_engine.BeginStep(adios2.StepMode.Append)
            self.timing_engine.Put("start", [self.start_time])
            self.timing_engine.Put("end", [self.end_time])
            self.timing_engine.Put("other", [self.other_time])
            self.timing_engine.EndStep()


    def Close(self):
        self.engine.Close()


