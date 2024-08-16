#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function, unicode_literals
import yaml
import re
import importlib.util
import sys
import os

if 'ADIOS' in os.environ:
    sys.path.insert(0, os.environ['ADIOS'])

import adios2
import numpy as np


def GetArgumentList(text):
    argstart = text.find('(') + 1
    astr = text[argstart:]

    alist = []
    opened = 0
    start = 0
    for i in range(len(astr)):
        if astr[i] == '(':
            opened += 1
        elif (astr[i] == ',') and (opened == 0):
            alist += [astr[start:i].strip()]
            start = i + 1
        elif astr[i] == ')':
            if (opened == 0):
                alist += [astr[start:i].strip()]
                break
            opened -= 1

    return alist


class MonitorGlobal:
    module = None
    setup = {}


class SpecialArg(object):
    def __init__(self, group, var):
        self.groupname = group
        self.varname = var


class IOSetup(object):

    def __init__(self, name, filename, code):
        self.code = code
        self.name = name
        self.filename = filename
        self.variables = []
        self.data = {}
        self.open = False
        self.found = False
        self.complete = False


class UserMonitor(object):

    def Declare(self):
        for group in self.IOSetups:
            #@effis-begin group->group
            self.IOSetups[group].io = adios.DeclareIO(group)
            #@effis-end


    def DoFunction(self):
        args = []
        for arg in self.args:
            if type(arg) == SpecialArg:
                args += [self.IOSetups[arg.groupname].data[arg.varname]]
            else:
                args += [arg]
        self.func(*args)


    def Open(self):
        opened = 0
        for group in self.IOSetups:

            if not self.IOSetups[group].open:
                try:
                    #@effis-begin self.IOSetups[group].io-->group
                    self.IOSetups[group].engine = self.IOSetups[group].io.Open(self.IOSetups[group].filename, adios2.Mode.Read)
                    #@effis-end
                except:
                    pass
                else:
                    self.IOSetups[group].open = True
                    
            if self.IOSetups[group].open:
                opened += 1

        if opened == len(self.IOSetups):
            self.AllOpen = True


    def Loop(self):
        if not self.AllOpen:
            self.Open()
        elif not self.finished:
            for groupname in self.IOSetups:
                #@effis-begin self.IOSetups[groupname].engine--->groupname
                status = self.IOSetups[groupname].engine.BeginStep(kittie.Kittie.ReadStepMode, 0.0)
                if status == adios2.StepStatus.OK:
                    for varname in self.IOSetups[groupname].variables:
                        varid = self.IOSetups[groupname].io.InquireVariable(varname)
                        shape = varid.Shape()
                        dtype = kittie.kittie_common.GetType(varid)
                        self.IOSetups[groupname].data[varname] = np.zeros(tuple(shape), dtype=dtype)
                        starts = np.zeros(len(shape), dtype=np.int64)
                        counts = np.array(shape, dtype=np.int64)
                        varid.SetSelection([starts, counts])
                        self.IOSetups[groupname].engine.Get(varid, self.IOSetups[groupname].data[varname])
                    self.IOSetups[groupname].engine.EndStep()
                    self.IOSetups[groupname].found = True
                elif status == adios2.StepStatus.EndOfStream:
                    if groupname not in self.complete:
                        self.complete += [groupname]
                #@effis-end

            if self.IOSetups[groupname].found and (status == adios2.StepStatus.OK):
                self.DoFunction()

            if len(self.complete) == len(self.IOSetups):
                self.finished = True
                for groupname in self.IOSetups:
                    #@effis-begin self.IOSetups[groupname].engine--->groupname
                    self.IOSetups[groupname].engine.Close()
                    #@effis-end

        if self.finished:
            return False
        else:
            return True


    def ParseArgs(self, FncTxt):
        match = self.ArgsSearch.search(FncTxt)

        if match is None:
            raise ValueError("Bad monitor statement: {0}{1}".format(FncTxt))

        else:
            fname = match.group(1).strip()
            estr = "self.func = MonitorGlobal.module.{0}".format(fname)
            exec(estr)
            argstr = match.group(2).strip()
            self.args = GetArgumentList(argstr)

            for i, arg in enumerate(self.args):
                special = False

                for code in MonitorGlobal.setup:

                    if arg.startswith(code) or arg.startswith('{' + code + '}'):
                        special = True
                        code, arg = kittie.kittie_common.DotSplit(arg)
                        groupname, varname = kittie.kittie_common.DotSplit(arg)
                        filename = MonitorGlobal.setup[code][groupname]['filename']

                        SetupName = "{0}-{1}".format(code, groupname)
                        if SetupName not in self.IOSetups:
                            self.IOSetups[SetupName] = IOSetup(groupname, filename, code)
                            if SetupName not in kittie.Kittie.YamlEngineSettings:
                                kittie.Kittie.YamlEngineSettings[SetupName] = MonitorGlobal.setup[code][groupname]
                        if varname not in self.IOSetups[SetupName].variables:
                            self.IOSetups[SetupName].variables += [varname]

                        self.args[i] = SpecialArg(SetupName, varname)
                        break

                if not special:
                    exec("self.args[i] = {0}".format(arg))


    def __init__(self, name, TxtCmd):
        self.ArgsSearch = re.compile("(.*)(\(.*\))")
        self.complete = []
        self.finished = False
        self.AllOpen = False
        self.name = name
        self.IOSetups = {}
        self.ParseArgs(TxtCmd)


class UserMonitors(object):

    def Loop(self):
        status = np.ones(len(self.monitors), dtype=np.bool_)
        while np.all(status):
            for i, key in enumerate(self.monitors.keys()):
                status[i] = self.monitors[key].Loop()


    def __init__(self, configfile=None, groupsfile=None):
        self.monitors = {}

        if groupsfile is None:
            groupsfile = "groups.yaml"
        with open(groupsfile, 'r') as ystream:
            MonitorGlobal.setup = yaml.load(ystream)

        if configfile is None:
            configfile = "monitor-config.yaml"
        with open(configfile, 'r') as ystream:
            config = yaml.load(ystream)

        spec = importlib.util.spec_from_file_location("module.name", config['filename'])
        MonitorGlobal.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(MonitorGlobal.module)

        calls = config['calls']
        for name in calls:
            self.monitors[name] = UserMonitor(name, calls[name])


if __name__ == "__main__":

    #@effis-init
    adios = adios2.ADIOS()
    Monitors = UserMonitors(configfile="monitor-config.yaml", groupsfile="groups.yaml")

    for key in Monitors.monitors:
        Monitors.monitors[key].Declare()
    Monitors.Loop()
    #@effis-finalize

