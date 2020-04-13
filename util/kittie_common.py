#!/usr/bin/env python

# Let's keep everything tested with python 2 and python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import numpy as np



def GetType(varid):
    size = varid.Sizeof()
    kind = varid.Type()

    # I'm just handling the common ones for now
    if kind.find('int') != -1:
        if size == 8:
            UserType = np.int64
        elif size == 4:
            UserType = np.int32
        elif size == 2:
            UserType = np.int16
    elif kind.find('double') != -1:
        UserType = np.float64
    elif (kind.find('float') != -1) or (kind.find('single') != -1):
        UserType = np.float32

    return UserType


def DotSplit(txt):
    if txt[0] == '{':
        EndIndex = '}'
        if EndIndex == -1:
            raise ValueError("Format for data can't be parsed correctly")
        entry = txt[1:EndIndex]

        if len(txt) > EndIndex + 2:
            remaining = txt[EndIndex + 2:]
        else:
            remaining = ""

    else:
        EndIndex = txt.find('.')
        if EndIndex == -1:
            raise ValueError("Format for data can't be parsed correctly")
        entry = txt[0:EndIndex]

        if len(txt) > EndIndex + 1:
            remaining = txt[EndIndex + 1:]
        else:
            remaining = ""

    return entry, remaining


def Namelist(*args):
    groups = []
    for arg in args:
        groups += ["&{0}{2}{1}{2}/\n".format(arg[0], arg[1], '\n\n')]
    outstr = "\n".join(groups)
    return outstr


def NMLFile(name, mainpath, outstr, codename=None, appname=None):
    outdir = os.path.join(mainpath, codename)

    if appname is None:
        outname = os.path.join(outdir, ".{0}.nml".format(name))
    else:
        outname = os.path.join(outdir, ".{0}-{1}.nml".format(name, appname))
    with open(outname, 'w') as out:
        out.write(outstr)

