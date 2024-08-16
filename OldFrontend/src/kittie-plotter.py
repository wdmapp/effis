#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function, unicode_literals
import yaml
import kittie
import adios2
import numpy as np
import argparse
import os
import re
from mpi4py import MPI

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


class PlotHelper(object):

    def __init__(self, name, config):

        self.name = name

        #for arg in ['filename', 'y']:
        for arg in ['filename']:
            if arg not in config:
                raise ValueError("{0}: '{1}' field must be given to make a plot".format(self.name, arg))
            exec("self.{0} = config[arg]".format(arg))

        if ('y' not in config) and ('image' not in config):
            raise ValueError("{0}: 'y' or 'image' field must be given to make a plot".format(self.name))

        for name, val in [('engine', 'BPFile'), ('x', None), ('y', None), ('image', None)]:
            if name not in config:
                value = val
            else:
                value = config[name]
            if type(value) is str:
                value = "'{0}'".format(value)
            string = "self.{0} = {1}".format(name, value)
            exec(string)

        self.step = 0
        kittie.Group(self.name, engine=self.engine)
        self.helper = kittie.Coupler(groupname=self.name)


    def GetSizer(self, instr):
        left = instr.find("[")
        if left != -1:
            return instr[:left]
        else:
            return instr


    def ParseShape(self, instr, shape, start):
        newshape = []
        left = instr.find("[")
        right = instr.find("]")
        if (left == -1) or (right == -1):
            return shape, start, shape

        selection = instr[(left+1):right]
        sels = selection.split(',')
        for i, sel in enumerate(sels):
            sel = sel.strip()
            pos = sel.find(':')
            if (pos == -1):
                start[i] = int(sel)
                shape[i] = 1
            else:
                if (pos != 0):
                    start[i] = int(sel[:pos])
                if (pos+1 != len(sel)):
                    shape[i] = int(sel[(pos+1):]) - start[i]
                newshape += [shape[i]]
        return shape, start, newshape


    def GetShaping(self, sizer):
        variables = self.helper.io.AvailableVariables()
        shape = variables[sizer]['Shape']
        shape = shape.strip().split(',')
        for i in range(len(shape)):
            shape[i] = int(shape[i])
        starts = np.zeros(len(shape), dtype=np.int64)
        return shape, starts


    def Plot(self, fs=20):
        print(self.name, self.step)

        if self.image is not None:
            oldimage = self.image
            self.image = self.GetSizer(self.image)
        else:
            oldy = self.y
            oldx = self.x
            self.y = self.GetSizer(self.y)
            self.x = self.GetSizer(self.x)

        data = {}

        if self.image is not None:
            shape, starts = self.GetShaping(self.image)
            shape, starts, newshape = self.ParseShape(oldimage, shape, starts)
            extent = [0, newshape[1], 0, newshape[0]]
            data['image'] = np.empty(tuple(newshape), dtype=np.float64)
            self.helper.GetSelection(data['image'], self.image, starts, shape)
            if self.y is not None:
                extent[2] = self.y[0]
                extent[3] = self.y[1]
            if self.x is not None:
                extent[0] = self.x[0]
                extent[1] = self.x[1]
        else:
            shape, starts = self.GetShaping(self.y)
            shape, starts, newshape = self.ParseShape(oldy, shape, starts)
            data['y'] = np.empty(tuple(newshape), dtype=np.float64)
            self.helper.GetSelection(data['y'], self.y, starts, shape)
            if self.x is not None:
                shape, starts = self.GetShaping(self.x)
                shape, starts, newshape = self.ParseShape(oldx, shape, starts)
                data['x'] = np.empty(tuple(newshape), dtype=np.float64)
                self.helper.GetSelection(data['x'], self.x, starts, shape)
            else:
                data['x'] = np.arange(newshpe[0])

        self.helper.EndStep()

        matplotlib.rcParams['axes.unicode_minus'] = False
        gs = gridspec.GridSpec(1, 1)
        fig = plt.figure(figsize=(7,6))
        ax = fig.add_subplot(gs[0, 0])

        if self.image is None:
            ax.plot(data['x'], data['y'])
            ax.set_ylabel(self.y.replace('_', '-'), fontsize=fs)
            if self.x is not None:
                ax.set_xlabel(self.x.replace('_', '-'), fontsize=fs)
            else:
                ax.set_xlabel('index')
            self.x = oldx
            self.y = oldy
        else:
            cax = ax.imshow(data['image'], extent=extent, origin="lower")
            cbar = fig.colorbar(cax)
            self.image = oldimage

        ax.set_title(self.name, fontsize=fs)
        fig.savefig(os.path.join("images", "{0}-{1}.png".format(self.name, self.step)), bbox_inches="tight")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    helpers = []
    comm = MPI.COMM_WORLD

    with open("kittie-plots.yaml", 'r') as ystream:
        config = yaml.load(ystream)

    if "mpmd" in config:
        rank = comm.Get_rank()
        comm = comm.Split(config["mpmd"], rank)
        del config["mpmd"]

    kittie.Initialize(comm=comm)
    for i, name in enumerate(config.keys()):
        helpers += [PlotHelper(name, config[name])]

    if not os.path.lexists("images"):
        os.makedirs("images")

    done = np.zeros(len(helpers), dtype=np.int)
    while True:

        if np.sum(done) == len(done):
            break

        for i in range(len(helpers)):

            if (done[i] == 1) or (not os.path.lexists(helpers[i].filename)):
                continue

            found = helpers[i].helper.BeginStep(filename=helpers[i].filename, groupname=helpers[i].helper.groupname, mode=adios2.Mode.Read, comm=comm, step=helpers[i].step, timeout=0.0)

            if found:
                helpers[i].Plot()
                helpers[i].step += 1
            else:
                fname = "{0}.done".format(helpers[i].filename)
                if os.path.lexists(fname):
                    done[i] = 1

