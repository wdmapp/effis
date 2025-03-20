#!/usr/bin/env python3

import omas
import effis.shim

import os
import argparse
import sys
import numpy as np

import adios2
import netCDF4


def vmec2bp_omas(filename=None, directory=None):

    if (filename is None) and (directory is None):
        raise ValueError("Must set filename or directory")
    elif (filename is not None) and (directory is not None):
        raise ValueError("Can't set both filename and directory")

    elif filename is not None:
        if not os.path.exists(filename):
            raise ValueError("Given file path does not exist: {0}".format(filename))
        files = [filename]

    elif directory is not None:
        if not os.path.exists(directory):
            raise ValueError("Given directory path does not exist: {0}".format(directory))
        #files = effis.composition.workflow.FindExt(directory, ext="out.nc", isdir=False)


    for filename in files:

        group = netCDF4.Dataset(filename)
        fsqt = group.variables["fsqt"][:]
        wdot = group.variables["wdot"][:]
        b0 = group.variables["b0"][:]

        ods = omas.ODS(consistency_check=False)
        ods["equilibrium.vacuum_toroidal_field.b0"] = b0

        for i in range(fsqt.shape[-1]):
            tsel = "equilibrium.time_slice.{i}.time".format(i=i)
            ods[tsel] = i + 1  # Colud also use: ods.set_time_array(tsel, i, i+1)
            fsel = "equilibrium.time_slice.{i}.fsqt".format(i=i)
            ods[fsel] = fsqt[i]
            wsel = "equilibrium.time_slice.{i}.wdot".format(i=i)  # Example that I've created, b/c wdot isn't documented in output and I wasn't sure what to match to in IMAS
            ods[wsel] = wdot[i]

        bppath = os.path.join(os.path.dirname(filename), os.path.splitext(os.path.basename(filename))[0])

        #effis.shim.save_omas_adios(ods, "ODS-vmec-01")
        effis.shim.save_omas_adios(ods, bppath)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename", help="Path to netCDF file", type=str, default=None)
    #parser.add_argument("-d", "--directory", help="Directory with files", type=str, default=None)
    parser.add_argument("-g", "--debug", help="Use debug prints", action="store_true")
    args = parser.parse_args()

    if args.debug:
        effis.shim.EffisLogger.SetDebug()

    #vmec2bp_omas(filename=args.filename, directory=args.directory)
    vmec2bp_omas(filename=args.filename, directory=None)


if __name__ == "__main__":

    main()

