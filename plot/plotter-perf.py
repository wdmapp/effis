#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import adios2
import argparse
import os
import sys
import plot_util

# I'm going to require MPI with this, it's more or less required to do anything else real
from mpi4py import MPI

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json


def Plot(data, StepNumber, outdir, fs=20):

    for name in data.keys():

        print(name, StepNumber); sys.stdout.flush()

        gs = gridspec.GridSpec(1, 1)
        fig = plt.figure(figsize=(7,6))
        ax = fig.add_subplot(gs[0, 0])

        x = [i for i in range(len(data[name]))]
        ax.plot(x, data[name].flatten())
        ax.set_ylabel(name, fontsize=fs)
        ax.set_title(name,  fontsize=fs)
        fig.savefig(os.path.join(outdir, "{0}_vs_rank-{1}.svg".format(name.replace('/', '|'), StepNumber)), bbox_inches="tight")
        plt.close(fig)


def ParseArgs():
    # Args are maybe just better in the dictionary
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--pattern", help="How to generate Y-value(s)", type=str, default=".*")
    parser.add_argument("-s", "--step", help="How to find step", type=str, default="step")
    parser.add_argument("-d", "--use-dashboard", help="Using dashboard", type=str, default="off")
    args = parser.parse_args()

    if args.use_dashboard.lower() in ["on", "yes", "true"]:
        args.use_dashboard = True
    else:
        args.use_dashboard = False

    return args


if __name__ == "__main__":
    matplotlib.rcParams['axes.unicode_minus'] = False
    args = ParseArgs()

    comm = MPI.COMM_WORLD

    #@effis-init comm=comm
    adios = adios2.ADIOS(comm)
    plotter = plot_util.KittiePlotter(comm, on=args.use_dashboard)
    plotter.ConnectToData()
    plotter.ConnectToStepInfo(adios, group="plotter")

    while plotter.NotDone:
        if plotter.DoPlot:
            HasStep = plotter.FindPlotData(args.pattern, args.step)
            if HasStep:
                Plot(plotter.data, plotter.StepNumber, plotter.outdir)
                plotter.StepDone()

    #@effis-finalize
