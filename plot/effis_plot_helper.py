#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import adios2
import sys
import re
import copy
import numpy as np
import kittie_common


class PlotterBase(object):

    def init(self, xaxis, yexpr, comm, xkind):
        self.xaxis = xaxis
        self.yexpr = yexpr
        self.comm = comm
        self.xkind = xkind

        self.rank = self.comm.Get_rank() 
        self.size = self.comm.Get_size()
        self.starts = None
        self.counts = None

        #@effis-begin "data"->"data"
        self.io = adios.DeclareIO("data")
        self.engine = self.io.Open("", adios2.Mode.Read, self.comm)

        if self.rank == 0:
            
            xvar = self.io.InquireVariable(self.xaxis)
            print(self.xaxis, xvar)
            if xvar is None:
                error = self.comm.bcast(1, root=0)
                raise ValueError("variable={0} was not found in data. Exiting.".format(self.xaxis))
            xshape = xvar.Shape()

            ynames = []
            ytypes = []
            pattern = re.compile(self.yexpr)
            variables = self.io.AvailableVariables()
            for name in variables.keys():
                match = pattern.search(name)
                if match is not None:
                    yvar = self.io.InquireVariable(name)
                    if yvar.Shape() != xshape:
                        print("{0} matches regular expression {1}, but does not match {2} in shape. Cannot plot it.".format(name, self.yexpr, self.xaxis))
                    elif name != self.xaxis:
                        ynames += [name]
                        ytypes += [kittie_common.GetType(yvar)]
                    elif self.xkind == "scatter":
                        ynames += [self.xaxis]
                        ytypes += [kittie_common.GetType(xvar)]

            if len(ynames) < 1:
                error = self.comm.bcast(1, root=0)
                raise RuntimeError("No matching axes with the same dimensions as {0} were found for regular exprssion {1}. Exiting".format(self.xaxis, self.yexpr))
            else:
                error = self.comm.bcast(None, root=0)

        else:
            error = self.comm.bcast(None, root=0)

        if error is not None:
            sys.exit()


        if self.rank == 0:
            yvars = [ [] ] * self.size
            ydts  = [ [] ] * self.size
            for i, name in enumerate(ynames):
                yvars[i%self.size] += [ynames[i]]
                ydts[i%self.size]  += [ytypes[i]]
            self.ynames = self.comm.scatter(yvars, root=0)
            self.ytypes = self.comm.scatter(ydts,  root=0)
            self.shape = self.comm.bcast(xshape, root=0)
            if self.xkind == "bcast":
                self.xtype = self.comm.bcast(kittie_common.GetType(xvar), root=0)
        else:
            self.ynames = self.comm.scatter(None, root=0)
            self.ytypes = self.comm.scatter(None, root=0)
            self.shape = self.comm.bcast(None, root=0)
            if self.xkind == "bcast":
                self.xtype = self.comm.bcast(None, root=0)


        if len(yvars) < 1:
            self.subcomm = self.comm.Split(1, self.rank)
            self.engine.Close()
            sys.exit(0)
        else:
            self.subcomm = self.comm.Split(0, self.rank)
        
        #@effis-end


    def MakeInt(self, dstr, size):
        try:
            dint = int(dstr.strip())
        except:
            raise ValueError("Dimension element {0} is not an integer".format(dstr))

        if dint < 0:
            dint = size + dint
        return dint


    def Selection(self, subselection, data, ndim):
        self.min = {}
        self.max = {}

        if (self.starts is None) and (self.counts is None):
            self.starts = [0] * (len(self.shape))
            self.counts = copy.copy(self.shape)
        
            if len(subselection.strip()) > 0:
                dims = subselection.split(',')
                if len(dims) != len(self.shape):
                    raise ValueError("Number of dimensions in subselection ({0}) does not match the number of dimensions in {1} ({2})".format(len(dims), self.xaxis, len(shape)))

                for i, dim in enumerate(dims):
                    d = dim.strip().split(':')
                    if len(d) == 1:
                        self.starts[i] = self.MakeInt(d[0], self.shape[i])
                        self.counts[i] = 1
                    elif len(d) == 2:
                        before = d[0].strip()
                        after = d[1].strip()
                        if len(before) > 0:
                            self.starts[i] = self.MakeInt(before, self.shape[i])
                        if len(after) > 0:
                            self.counts[i] = self.MakeInt(after, self.shape[i]) - self.starts[i]
                    else:
                        raise ValueError("Something is wrong in subdimension {0}: {1}".format(i, dim))

                    if self.starts[i] >= self.shape[i]:
                        raise ValueError("In dimension {0}, start selection of {1} is beyond the dimension's shape of {2}".format(i, self.starts[i], self.shape[i]))
                    if self.counts[i] < 1:
                        raise ValueError("In dimension {1}, selection count of {0} does not make sense".format(i, self.counts[i]))
                    if (self.starts[i] + self.counts[i]) > self.shape[i]:
                        raise ValueError("In dimension {0}, selection start of {1} and count of {2} goes beyond dimemsion shape of {3}".format(i, self.starts[i], self.counts[i], self.shape[i]))

                cut = (np.array(self.counts) > 1)
                if (np.sum(cut) > ndim):
                    raise ValueError("More than {1} dimension(s) in {0} is greater than one".format(subselection, ndim))

            if self.xkind == "bcast":
                self.ynames += [self.xaxis]
                self.ytypes += [self.xtype]

            for yname, ytype in zip(self.ynames, self.ytypes):
                if yname not in data:
                    data[yname] = np.empty(self.counts, dtype=ytype)
        
        for yname in self.ynames + [self.xaxis]:
            var = self.io.InquireVariable(yname)
            var.SetSelection([self.starts, self.counts])
            self.engine.Get(var, data[yname])
            
            variables = self.io.AvailableVariables()
            self.min[yname] = float(variables[yname]['Min'])
            self.max[yname] = float(variables[yname]['Max'])

        return data

