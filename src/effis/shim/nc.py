#!/usr/bin/env python3

import os
import argparse
import numpy as np

import netCDF4
import adios2
import effis.composition


def RecurseNC(group, io, engine, scope=None):

    # Attributes
    for attrname in group.__dict__:
        name = attrname
        if scope is not None:
            attrname = os.path.join(scope, attrname)
        io.define_attribute(attrname, group.__dict__[name])

    # Variables
    for varname in group.variables:
        name = varname
        if scope is not None:
            varname = os.path.join(scope, varname)

        shape = group.variables[name].shape
        if len(shape) == 0:
            arr = group.variables[name][:]
            varid = io.define_variable(varname, arr)
        else:
            if (group.variables[name].dtype.char == "S") and (group.variables[name].dtype.itemsize == 1) and (group.variables[name][:].ndim == 1):
                arr = list(group.variables[name][:])
                for i in range(len(arr)):
                    try:
                        arr[i] = arr[i].decode('UTF-8')
                    except:
                        arr[i] = ""
                arr = ''.join(arr)
                varid = io.define_variable(varname, arr)
            elif (group.variables[name].dtype.char == "S") and (group.variables[name].dtype.itemsize == 1) and (group.variables[name][:].ndim > 1):
                effis.composition.EffisLogger.Warning("Skipping {0} -- string array".format(name))
                continue
            else:
                arr = group.variables[name][:]
                varid = io.define_variable(varname, arr, shape, np.zeros(group.variables[name].ndim, dtype=np.int64), shape)

        engine.write(varid, arr)
        if len(shape) > 0:
            # Record dimensions
            if type(group.variables[name].dimensions) is tuple:
                io.define_attribute("dimensions", list(group.variables[name].dimensions), varname)
            else:
                io.define_attribute("dimensions", group.variables[name].dimensions, varname)

        # Variable attributes
        for key in group.variables[name].__dict__:
            attr = group.variables[name].__dict__[key]
            # ADIOS attributes don't understand numpy byte strings
            if (type(attr) is np.ndarray) and (attr.dtype.char == "S"):
                attr = list(attr)
            io.define_attribute(key, attr, varname)

    # Child groups
    for groupname in group.groups:
        newscope = groupname
        if scope is not None:
            newscope = os.path.join(scope, newscope)
        RecurseNC(group.groups[groupname], io, engine, scope=newscope)


def nc2bp(filename=None, directory=None):

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
        files = effis.composition.workflow.FindExt(directory, ext=".nc", isdir=False)


    for filename in files:

        f = netCDF4.Dataset(filename)

        ioname = os.path.splitext(os.path.basename(filename))[0]
        adios = adios2.Adios()
        io = adios.declare_io(ioname)
        bpfile = os.path.join(os.path.dirname(filename), "{0}.bp".format(ioname))
        engine = adios2.Stream(io, bpfile, "w")

        engine.begin_step()
        RecurseNC(f, io, engine)
        engine.end_step()
        engine.close()

        effis.composition.EffisLogger.Info("Wrote {0}".format(bpfile))


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename", help="Path to netCDF file", type=str, default=None)
    parser.add_argument("-d", "--directory", help="Directory with files", type=str, default=None)
    args = parser.parse_args()

    nc2bp(filename=args.filename, directory=args.directory)


if __name__ == "__main__":

    main()

