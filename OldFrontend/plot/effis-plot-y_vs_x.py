#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function, unicode_literals

import adios2
import argparse
import os
import sys
import re
import numpy as np
from effis_plot_helper import PlotterBase

# I'm going to require MPI with this, it's more or less required to do anything else real
from mpi4py import MPI

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


class Plotter1D(PlotterBase):

    def __init__(self, xaxis, yexpr, comm): 
        self.init(xaxis, yexpr, comm, "bcast")


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
        
        data = plotter.Selection(args.subselection, data, 1)
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

