#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import adios2
import argparse
import os
import sys
import re
import copy
import numpy as np
from effis_plot_helper import PlotterBase
import kittie_common

# I'm going to require MPI with this, it's more or less required to do anything else real
from mpi4py import MPI

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.tri as tri


class PlotterPlane(PlotterBase):

    def __init__(self, yexpr, comm): 
        self.init("dpot", yexpr, comm, "scatter")


    def Plot(self, data, outdir, ext, fs=20, cmap="bwr", nlevels=100, xmax=10, ymax=8, kind={'name': 'minmax'}):

        levels = nlevels
        for name in data.keys():

            imagename = os.path.join(outdir, "{0}.{1}".format(name, ext))
            print(imagename, np.amin(data[name]), np.amax(data[name])); sys.stdout.flush()

            gs = gridspec.GridSpec(nrows=1, ncols=1)
            fig = plt.figure(tight_layout=True)
            ax = fig.add_subplot(gs[0])

            kwargs = {}

            if kind['name'] == "minmax":
                opt = np.amax(np.fabs([self.min[name], self.max[name]]))
            elif kind['name'] == "percentile":
                if "value" not in kind:
                    kind['value'] = 95
                opt = np.percentile(np.fabs(data[name]), kind['value'])

            kwargs['cmap'] = plt.get_cmap(cmap)
            kwargs['extend'] = "both"
            kwargs['cmap'].set_under(kwargs['cmap'](0))
            kwargs['cmap'].set_over(kwargs['cmap'](1.0))

            levels = np.linspace(-opt, opt, nlevels)
            ColorAxis = ax.tricontourf(self.triang, data[name].flatten(), levels, **kwargs)

            ColorBar = fig.colorbar(ColorAxis, ax=ax, format="%+.1e", pad=0, extendrect=True)
            ColorBar.set_label(name, fontsize=fs)
            ticks = np.linspace(-opt, opt, 7)
            ColorBar.set_ticks(ticks)
            ColorBar.ax.tick_params(labelsize=int(fs*0.66))

            ax.set_aspect(1)
            ax.set_xlabel("r", fontsize=fs)
            ax.set_ylabel("z", fontsize=fs)
            ax.set_title("{0}".format(name),  fontsize=fs)
            ax.tick_params(axis='both', which='major', labelsize=fs)
            xsize, ysize = fig.get_size_inches()

            while True:
                xnew = xsize * 1.05
                ynew = ysize * 1.05
                if (xnew < xmax) and (ynew < ymax):
                    xsize = xnew
                    ysize = ynew
                else:
                    fig.set_size_inches(xsize, ysize)
                    break

            fig.savefig(imagename, bbox_inches="tight")
            plt.close(fig)


    def ReadMesh(self, nodesname="rz", triname="nd_connect_list"):
        meshfile = None
        #@effis-begin "mesh"->"mesh"
        io = adios.DeclareIO("mesh")
        engine = io.Open(meshfile, adios2.Mode.Read)
        engine.BeginStep()

        NodesVar = io.InquireVariable(nodesname)
        dtype = kittie_common.GetType(NodesVar)
        dims = NodesVar.Shape()
        self.nodes = np.zeros(tuple(dims), dtype=dtype)
        NodesVar.SetSelection([[0]*len(dims), list(dims)])
        engine.Get(NodesVar, self.nodes)

        TriVar = io.InquireVariable(triname)
        dtype = kittie_common.GetType(TriVar)
        dims = TriVar.Shape()
        self.triangles = np.zeros(tuple(dims), dtype=dtype)
        TriVar.SetSelection([[0]*len(dims), list(dims)])
        engine.Get(TriVar, self.triangles)

        engine.EndStep()
        #@effis-end

        self.triang = tri.Triangulation(self.nodes[:, 0], self.nodes[:, 1], triangles=self.triangles)

           
def ParseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("yexpr", help="Regular expression for y-axis variables to select", type=str, default=[])
    parser.add_argument("-e", "--ext", help="Image extension", type=str, default="png", choices=["png", "svg"])
    parser.add_argument("-p", "--plane", help="Poloidal plane selection", type=int, default=0)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    matplotlib.rcParams['axes.unicode_minus'] = False
    args = ParseArgs()
    subselection = "{0}, :".format(args.plane)

    comm = MPI.COMM_WORLD
    data = {}
    i = 0


    #@effis-init comm=comm
    adios = adios2.ADIOS(comm)

    plotter = PlotterPlane(args.yexpr, comm)
    plotter.ReadMesh()

    #@effis-begin plotter.engine--->"data"
    while(True):
        status = plotter.engine.BeginStep()
        if (status == adios2.StepStatus.NotReady):
            continue
        elif (status != adios2.StepStatus.OK):
            break
        
        data = plotter.Selection(subselection, data, 1)
        plotter.engine.EndStep()

        outdir = os.path.join("output", "{0}".format(i))
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        plotter.subcomm.Barrier()

        plotter.Plot(data, outdir, args.ext, fs=16, kind={'name': 'percentile', 'value': 99.5})
        #plotter.Plot(data, outdir, args.ext, fs=16, kind={'name': 'minmax'})
        #@effis-plot name="xgc-plane", steps="data", directory=outdir
        i += 1

    plotter.engine.Close()
    #@effis-end

    #@effis-finalize

