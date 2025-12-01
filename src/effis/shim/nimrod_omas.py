#!/usr/bin/env python3

import omas
import effis.shim
import effis.composition

import os
import argparse
import sys
import numpy as np

import adios2
import netCDF4


def Varname(varname, prefix=""):
    return prefix + varname


def adios_with_omas(filename=None, directory=None, time=None, prefix=None):

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
        files = effis.composition.workflow.FindExt(directory, ext="bp", isdir=True)

    
    for filename in files:

        ods = omas.ODS(consistency_check=False)

        print(filename)
        with adios2.FileReader(filename) as infile:

            variables = infile.available_variables()
            data = {}

            count = 0

            if time is None:
                time = 0

            if prefix is None:
                prefix = ""

            for name in ("field-xy", "field-rt"):

                v = Varname("blocks" + "/" + name, prefix=prefix)
                m = v.replace("field", "mesh")

                if v in variables:
                    field = infile.read(v)
                    mesh = infile.read(m)

                    #ods["mhd.ggd.{time}.mass_density.{grid_subset/grid_index}.values".format(count)] = field.flatten()
                    ods["mhd.ggd.{0}.mass_density.{1}.values".format(time, count)] = field.flatten()
                    ods["mhd.ggd.{0}.mass_density.{1}.grid_index".format(time, count)] = count
                    #ods["mhd.ggd.{0}.mass_density.{1}.grid_subset_index".format(time, count)] = 0  # 5

                    ods["mhd.ggd.{0}.space.{1}.geometry_type.index".format(time, count)] = 0    # 0 for spatial, 1 for Fourier, > 1 for Fourier with periodicity
                    ods["mhd.ggd.{0}.space.{1}.geometry_type.name".format(time, count)] = v[-2:]
                    #ods["mhd.ggd.{0}.space.{1}.identifier.index".format(time, count)] = 0

                    ods["mhd.grid_ggd.{0}.space.{1}.objects_per_dimension.{2}.geometry_content.index".format(time, count, 0)] = 4     # Cells/volume
                    ods["mhd.grid_ggd.{0}.space.{1}.objects_per_dimension.{2}.geometry_content.description".format(time, count, 0)] = "2D grid"

                    size = field.shape[0] * field.shape[1]
                    ods["mhd.grid_ggd.{0}.space.{1}.objects_per_dimension.{2}.object.geometry".format(time, count, 0)] = np.zeros((size, 2), np.float64)
                    ods["mhd.grid_ggd.{0}.space.{1}.objects_per_dimension.{2}.object.geometry".format(time, count, 0)][:, 0] = mesh[:, :, 0].flatten()
                    ods["mhd.grid_ggd.{0}.space.{1}.objects_per_dimension.{2}.object.geometry".format(time, count, 0)][:, 1] = mesh[:, :, 1].flatten()

                    '''
                    for i in range(size):
                        ods["mhd.grid_ggd.{0}.space.{1}.objects_per_dimension.{2}.object.{3}.geometry".format(time, count, 0, i)] = [0, 0]
                    '''

                    count += 1


        bppath = "imas" 
        effis.shim.save_omas_adios(ods, bppath)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename", help="Path to netCDF file", type=str, default=None)
    parser.add_argument("-d", "--directory", help="Directory with files", type=str, default=None)
    parser.add_argument("-t", "--time", help="Time step", type=str, default=None)
    parser.add_argument("-p", "--prefix", help="Prefix", type=str, default=None)
    parser.add_argument("-g", "--debug", help="Use debug prints", action="store_true")
    args = parser.parse_args()

    if args.debug:
        effis.shim.EffisLogger.SetDebug()

    adios_with_omas(filename=args.filename, directory=args.directory, time=args.time, prefix=args.prefix)



if __name__ == "__main__":

    main()

