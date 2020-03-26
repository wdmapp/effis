#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import adios2
import argparse
import os
import sys
import numpy as np
import plot_util
import kittie_common

# I'm going to require MPI with this, it's more or less required to do anything else real
from mpi4py import MPI

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.tri as tri
from matplotlib.ticker import FormatStrFormatter


def Plot(data, nodesname, triname, outdir, fs=20, xname="x", yname="y", cmap="bwr", nlevels=40, minmax=False):

    levels = nlevels
    for name in data.keys():
        if name in ['_StepPhysical', '_StepNumber', nodesname, triname, 'minmax']:
            continue

        print(name, data['_StepNumber'], data['_StepPhysical']); sys.stdout.flush()

        gs = gridspec.GridSpec(1, 1)
        fig = plt.figure(figsize=(7,6))
        ax = fig.add_subplot(gs[0, 0])

        kwargs = {}
        kwargs['cmap'] = plt.get_cmap(cmap)
        if minmax:
            opt = np.amax(np.fabs([data['minmax'][name]['min'], data['minmax'][name]['max']])) + 1e-20
            kwargs['vmin'] = -opt
            kwargs['vmax'] = opt
            nlevels = np.linspace(-opt, opt, levels)

        triang = tri.Triangulation(data[nodesname][:, 0], data[nodesname][:, 1], triangles=data[triname])
        ColorAxis = ax.tricontourf(triang, data[name].flatten(), nlevels, **kwargs)
        ColorBar = fig.colorbar(ColorAxis, ax=ax, format="%+.2e")
        ColorBar.set_label(name, fontsize=fs)
        if minmax:
            ticks = np.linspace(-opt, opt, 7)
            ColorBar.set_ticks(ticks)

        ax.set_xlabel(xname, fontsize=fs)
        ax.set_ylabel(yname, fontsize=fs)
        ax.set_title("{1},  time = {0:.1e}".format(data['_StepPhysical'][0], name),  fontsize=fs)

        fig.savefig(os.path.join(outdir, "{0}_vs_{2}_{3}-{1}.svg".format(name, data['_StepNumber'][0], xname, yname)), bbox_inches="tight")
        plt.close(fig)


def ReadMesh(nodesname, triname, griddata={}):
    meshfile = None
    #@effis-begin "mesh"->"mesh"
    io = adios.DeclareIO("mesh")
    engine = io.Open(meshfile, adios2.Mode.Read)
    engine.BeginStep()

    NodesVar = io.InquireVariable(nodesname)
    dtype = kittie_common.GetType(NodesVar)
    dims = NodesVar.Shape()
    griddata[nodesname] = np.zeros(tuple(dims), dtype=dtype)
    NodesVar.SetSelection([[0]*len(dims), list(dims)])
    engine.Get(NodesVar, griddata[nodesname])

    TriVar = io.InquireVariable(triname)
    dtype = kittie_common.GetType(TriVar)
    dims = TriVar.Shape()
    griddata[triname] = np.zeros(tuple(dims), dtype=dtype)
    TriVar.SetSelection([[0]*len(dims), list(dims)])
    engine.Get(TriVar, griddata[triname])

    engine.EndStep()
    #@effis-end

    return griddata


def ParseArgs():
    # Args are maybe just better in the dictionary
    parser = argparse.ArgumentParser()
    parser.add_argument("nodes", help="(x,y) coordinates of nodes")
    parser.add_argument("triangles", help="Triangle tuples matching into nodes array")
    parser.add_argument("gridvar", help="One grid variable to match to")
    parser.add_argument("-o", "--only",     help="Only plot the given y-values", type=str, default=[])
    parser.add_argument("-e", "--exclude",  help="Don't plot the given y-values", type=str, default=[])
    parser.add_argument("-c", "--colormap", help="Colormap to use", type=str, default="bwr")
    parser.add_argument("-n", "--nlevels",  help="Number of color levels", type=int, default=40)
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
    plotter.ConnectToStepInfo(adios, group="plotter")
    plotter.GetMatchingSelections(adios, args.gridvar, exclude=args.exclude, only=args.only, xomit=False, allx=False)

    plotter.data = ReadMesh(args.nodes, args.triangles, griddata=plotter.data)

    if plotter.Active:

        while plotter.NotDone:

            if plotter.DoPlot:
                plotter.GetPlotData()
                Plot(plotter.data, args.nodes, args.triangles, plotter.outdir, xname="r", yname="z", cmap=args.colormap, nlevels=args.nlevels, minmax=True)
                plotter.StepDone()

    #@effis-finalize

