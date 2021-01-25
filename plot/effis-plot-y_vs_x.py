#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import adios2
import argparse
import os
import sys
import re
import copy
import numpy as np
import kittie_common

# I'm going to require MPI with this, it's more or less required to do anything else real
from mpi4py import MPI

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json



class Plotter1D(object):

    def __init__(self, xaxis, yexpr, comm): 
        self.comm = comm
        self.rank = self.comm.Get_rank() 
        self.size = self.comm.Get_size()
        self.xaxis = xaxis
        self.starts = None
        self.counts = None

        #@effis-begin "data"->"data"
        self.io = adios.DeclareIO("data")
        self.engine = self.io.Open("", adios2.Mode.Read, self.comm)

        if self.rank == 0:
            
            xvar = self.io.InquireVariable(xaxis)
            if xvar is None:
                error = self.comm.bcast(1, root=0)
                raise ValueError("xaxis={0} was not found in data. Exiting.".format(xaxis))
            xshape = xvar.Shape()

            ynames = []
            ytypes = []
            pattern = re.compile(yexpr)
            variables = self.io.AvailableVariables()
            for name in variables.keys():
                match = pattern.search(name)
                if match is not None:
                    yvar = self.io.InquireVariable(name)
                    if yvar.Shape() != xshape:
                        print("{0} matches regular expression {1}, but does not match {2} in shape. Cannot plot it.".format(name, yexpr, xaxis))
                    else:
                        ynames += [name]
                        ytypes += [kittie_common.GetType(yvar)]

            if len(ynames) < 1:
                error = self.comm.bcast(1, root=0)
                raise RuntimeError("No matching axes with the same dimensions as {0} were found for regular exprssion {1}. Exiting".format(xaxis, yexpr))
            else:
                error = self.comm.bcast(None, root=0)

        else:
            error = self.comm.bcast(None, root=0)

        if error is not None:
            sys.exit()


        if self.rank == 0:
            yvars = [ [] ] * self.size
            ydts  = [ [] ] * self.size
            for i, name in enumerate(ynames):
                yvars[i%self.size] += [ynames[i]]
                ydts[i%self.size]  += [ytypes[i]]
            self.ynames = self.comm.scatter(yvars, root=0)
            self.ytypes = self.comm.scatter(ydts,  root=0)
            self.shape = self.comm.bcast(xshape, root=0)
            self.xtype = self.comm.bcast(kittie_common.GetType(xvar), root=0)
        else:
            self.ynames = self.comm.scatter(None, root=0)
            self.ytypes = self.comm.scatter(None, root=0)
            self.shape = self.comm.bcast(None, root=0)
            self.xtype = self.comm.bcast(None, root=0)


        if len(yvars) < 1:
            self.subcomm = self.comm.Split(1, self.rank)
            self.engine.Close()
            sys.exit(0)
        else:
            self.subcomm = self.comm.Split(0, self.rank)
        
        #@effis-end


    def Plot(self, data, outdir, ext, fs=20):

        for name in data.keys():
            if name == self.xaxis:
                continue

            imagename = os.path.join(outdir, "{0}_vs_{1}.{2}".format(name, self.xaxis, ext))
            print(imagename, np.amin(data[name]), np.amax(data[name])); sys.stdout.flush()

            gs = gridspec.GridSpec(1, 1)
            fig = plt.figure(figsize=(7,6))
            ax = fig.add_subplot(gs[0, 0])

            ax.plot(data[self.xaxis], data[name])
            ax.set_xlabel(self.xaxis, fontsize=fs)
            ax.set_ylabel(name,       fontsize=fs)

            fig.savefig(imagename, bbox_inches="tight")
            plt.close(fig)


    def MakeInt(self, dstr, size):
        try:
            dint = int(dstr.strip())
        except:
            raise ValueError("Dimension element {0} is not an integer".format(dstr))

        if dint < 0:
            dint = size + dint
        return dint


    def Selection(self, subselection, data):

        if (self.starts is None) and (self.counts is None):
            self.starts = [0] * (len(self.shape))
            self.counts = copy.copy(self.shape)
        
            if len(subselection.strip()) > 0:
                dims = subselection.split(',')
                if len(dims) != len(self.shape):
                    raise ValueError("Number of dimensions in subselection ({0}) does not match the number of dimensions in {1} ({2})".format(len(dims), self.xaxis, len(shape)))

                for i, dim in enumerate(dims):
                    d = dim.strip().split(':')
                    if len(d) == 1:
                        self.starts[i] = self.MakeInt(d[0], self.shape[i])
                        self.counts[i] = 1
                    elif len(d) == 2:
                        before = d[0].strip()
                        after = d[1].strip()
                        if len(before) > 0:
                            self.starts[i] = self.MakeInt(before, self.shape[i])
                        if len(after) > 0:
                            self.counts[i] = self.MakeInt(after, self.shape[i]) - self.starts[i]
                    else:
                        raise ValueError("Something is wrong in subdimension {0}: {1}".format(i, dim))

                    if self.starts[i] >= self.shape[i]:
                        raise ValueError("In dimension {0}, start selection of {1} is beyond the dimension's shape of {2}".format(i, self.starts[i], self.shape[i]))
                    if self.counts[i] < 1:
                        raise ValueError("In dimension {1}, selection count of {0} does not make sense".format(i, self.counts[i]))
                    if (self.starts[i] + self.counts[i]) > self.shape[i]:
                        raise ValueError("In dimension {0}, selection start of {1} and count of {2} goes beyond dimemsion shape of {3}".format(i, self.starts[i], self.counts[i], self.shape[i]))

                cut = (np.array(self.counts) > 1)
                if (np.sum(cut) > 1):
                    raise ValueError("More than one dimension in {0} is greater than one".format(subselection))

            for yname, ytype in zip(self.ynames + [self.xaxis], self.ytypes + [self.xtype]):
                if yname not in data:
                    data[yname] = np.empty(self.counts, dtype=ytype)
        
        for yname in self.ynames + [self.xaxis]:
            var = self.io.InquireVariable(yname)
            var.SetSelection([self.starts, self.counts])
            self.engine.Get(var, data[yname])

        return data

           
def ParseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("xaxis", help="What to use as x-axis for plotting")
    parser.add_argument("yexpr", help="Regular expression for y-axis variables to select", type=str, default=[])
    parser.add_argument("-e", "--ext", help="Image extension", type=str, default="png", choices=["png", "svg"])
    parser.add_argument("-s", "--subselection", help="Subselection for variables", type=str, default="")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    matplotlib.rcParams['axes.unicode_minus'] = False
    args = ParseArgs()
    comm = MPI.COMM_WORLD
    data = {}
    i = 0

    #@effis-init comm=comm
    adios = adios2.ADIOS(comm)

    plotter = Plotter1D(args.xaxis, args.yexpr, comm)

    #@effis-begin plotter.engine--->"data"
    while(True):
        status = plotter.engine.BeginStep()
        if (status == adios2.StepStatus.NotReady):
            continue
        elif (status != adios2.StepStatus.OK):
            break
        
        data = plotter.Selection(args.subselection, data)
        plotter.engine.EndStep()

        outdir = os.path.join("output", "{0}".format(i))
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        plotter.subcomm.Barrier()

        plotter.Plot(data, outdir, args.ext)
        #@effis-plot name="1D", steps="data", directory=outdir
        i += 1

    plotter.engine.Close()
    #@effis-end

    #@effis-finalize

