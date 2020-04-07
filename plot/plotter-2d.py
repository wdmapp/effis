#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import adios2
import argparse
import os
import sys
import numpy as np
import plot_util
import sys

# I'm going to require MPI with this, it's more or less required to do anything else real
from mpi4py import MPI

import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

inits = {}
gs = {}
fig = {}
ax = {}
kwargs = {}
ColorAxis = {}
ColorBar = {}


def Plot(data, outdir, fs=20, xname="x", yname="y", cmap="bwr", minmax=False, interactive="image", ext="svg"):

    for name in data.keys():
        if name in ['_StepPhysical', '_StepNumber', 'minmax']:
            continue
        print(name, data['_StepNumber'], data['_StepPhysical']); sys.stdout.flush()

        if name not in inits:
            inits[name] = False

        if not inits[name]:
            gs[name] = gridspec.GridSpec(1, 1)
            fig[name] = plt.figure(figsize=(7,6), tight_layout=True)
            ax[name] = fig[name].add_subplot(gs[name][0, 0])
            kwargs[name] = {}
            kwargs[name]['cmap'] = plt.get_cmap(cmap)
            kwargs[name]['origin'] = "lower"
        if minmax:
            opt = np.amax(np.fabs([data['minmax'][name]['min'], data['minmax'][name]['max']])) + 1e-20
            kwargs[name]['vmin'] = -opt
            kwargs[name]['vmax'] = opt

        if not inits[name]:
            ColorAxis[name] = ax[name].imshow(data[name].squeeze(), **(kwargs[name]))
            ColorBar[name] = fig[name].colorbar(ColorAxis[name], ax=ax[name], format="%+.2e")
            ColorBar[name].set_label(name, fontsize=fs)
            ax[name].set_xlabel(xname, fontsize=fs)
            ax[name].set_ylabel(yname, fontsize=fs)
        else:
            ColorAxis[name].set_data(data[name].squeeze())
            if minmax:
                ColorAxis[name].set_clim(cmin=kwargs[name]['vmin'], cmax=kwargs[name]['vmax'])
            else:
                ColorAxis[name].autoscale()

        ax[name].set_title("{1},  time = {0:.1e}".format(data['_StepPhysical'][0], name),  fontsize=fs)
        if minmax:
            ticks = np.linspace(-opt, opt, 7)
            ColorBar[name].set_ticks(ticks)

        if not inits[name]:
            inits[name] = True
        else:
            if interactive != 'image':
                fig[name].tight_layout()
                fig[name].canvas.draw()
                fig[name].canvas.flush_events()

        if interactive != "interactive":
            fig[name].savefig(os.path.join(outdir, "{0}_vs_{2}_{3}-{1}.{4}".format(name.replace('/', '|'), data['_StepNumber'][0], xname, yname, ext)), bbox_inches="tight")

        #plt.close(fig)
        



def ParseArgs():
    # Args are maybe just better in the dictionary
    parser = argparse.ArgumentParser()
    parser.add_argument("gridvar", help="One grid variable to match to")
    parser.add_argument("-o", "--only",     help="Only plot the given y-values", type=str, default=[])
    parser.add_argument("-e", "--exclude",  help="Don't plot the given y-values", type=str, default=[])
    parser.add_argument("-c", "--colormap", help="Colormap to use", type=str, default="bwr")
    parser.add_argument("-t", "--type", help="Image file and/or interactive", type=str, default="image", choices=["image", "interactive", "both"])
    parser.add_argument("-x", "--ext", help="Image extension", type=str, default="svg", choices=["svg", "png"])
    parser.add_argument("-d", "--use-dashboard", help="Using dashboard", type=str, default="off")

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
    plotter.GetMatchingSelections(adios, args.gridvar, exclude=args.exclude, only=args.only, xomit=False, allx=False)
    plotter.ConnectToStepInfo(adios, group="plotter")

    if args.type != "image":
        plt.ion()

    force = True
    while force or plotter.NotDone:

        if force or plotter.DoPlot:
            plotter.GetPlotData()
            if plotter.Active:
                Plot(plotter.data, plotter.outdir, xname="x", yname="y", cmap=args.colormap, minmax=False, interactive=args.type, ext=args.ext)
            plotter.StepDone()
        force = False

    #@effis-finalize

