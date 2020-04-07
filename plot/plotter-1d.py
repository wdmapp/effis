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


def Plot(data, xname, outdir, fs=20):

    for name in data.keys():
        if name in ['_StepPhysical', '_StepNumber', xname, 'minmax']:
            continue

        print(xname, name, data['_StepNumber'], data['_StepPhysical']); sys.stdout.flush()

        gs = gridspec.GridSpec(1, 1)
        fig = plt.figure(figsize=(7,6))
        ax = fig.add_subplot(gs[0, 0])

        ax.plot(data[xname].flatten(), data[name].flatten())
        ax.set_xlabel(xname, fontsize=fs)
        ax.set_ylabel(name,  fontsize=fs)
        ax.set_title("{1},  time = {0:.1e}".format(data['_StepPhysical'][0], name),  fontsize=fs)

        fig.savefig(os.path.join(outdir, "{0}_vs_{1}-{2}.svg".format(name.replace('/', '|'), xname.replace('/', '|'), data['_StepNumber'][0])), bbox_inches="tight")
        plt.close(fig)

def Plotly(data, xname, outdir):

    for name in data.keys():
        if name in ['_StepPhysical', '_StepNumber', xname, 'minmax']:
            continue

        result = {
            'data': [{'mode': 'line', 'type': 'scatter', 'x': data[xname].tolist(), 'y': data[name].tolist()}],
            'layout': {
                'title': '{1},  time = {0:.1e}'.format(data['_StepPhysical'][0], name),
                'autosize': 'true', 'hovermode': 'closest',
                'xaxis': {'type': 'linear', 'range': 'auto', 'title': str(xname), 'autorange': 'false'},
                'yaxis': {'type': 'linear', 'range': 'auto', 'title': str(name), 'autorange': 'false'},
            }, 'frames': []
        }

        output_file = os.path.join(
            outdir, "{0}_vs_{1}-{2}.json".format(name.replace('/', '|'), xname.replace('/', '|'), data['_StepNumber'][0]))

        with open(output_file, 'w') as f:
            json.dump(result, f)

def StepFile(data, outdir):

    #output_file = os.path.join(outdir, "{0}".format(data['_StepNumber'][0]))

    with adios2.open(outdir, 'w') as f:
        for name in data.keys():
            if name in ['_StepPhysical', '_StepNumber', 'minmax']:
                continue
            array = data[name]
            shape = list(array.shape)
            count = [array.size]
            start = [] if shape == [] else [0]
            f.write(name, array, shape, start, count)

def ParseArgs():
    # Args are maybe just better in the dictionary
    parser = argparse.ArgumentParser()
    parser.add_argument("xaxis", help="What to use as x-axis for plotting")
    parser.add_argument("-o", "--only",     help="Only plot the given y-values", type=str, default=[])
    parser.add_argument("-e", "--exclude", help="Don't plot the given y-values", type=str, default=[])
    parser.add_argument("-y", "--y", help="How to generate Y-value(s)", type=str, default="match-dimensions")
    parser.add_argument("-d", "--use-dashboard", help="Using dashboard", type=str, default="off")
    parser.add_argument("-out", "--output", help="Which output format to provide", type=str, default="plot")
    args = parser.parse_args()

    if len(args.only) > 0:
        args.only = args.only.split(',')
    if len(args.exclude) > 0:
        args.exclude = args.exclude.split(',')

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
    plotter.GetMatchingSelections(adios, args.xaxis, exclude=args.exclude, only=args.only, xomit=True, y=args.y)
    plotter.ConnectToStepInfo(adios, group="plotter")


    force = True
    while force or plotter.NotDone:

        if force or plotter.DoPlot:
            plotter.GetPlotData(y=args.y)

            if plotter.Active:
                if args.output and args.output.lower() == 'bp':
                    StepFile(plotter.data, plotter.outdir)
                elif args.output and args.output.lower() == 'plotly':
                    Plotly(plotter.data, plotter.DimInfo['xname'], plotter.outdir)
                elif not args.output or args.output.lower() == 'matplot':
                    Plot(plotter.data, plotter.DimInfo['xname'], plotter.outdir)

            plotter.StepDone()
        force = False

    #@effis-finalize
