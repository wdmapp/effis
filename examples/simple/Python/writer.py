#!/usr/bin/env python3

import adios2
import random
import numpy as np
import time
import sys
import socket

class mpi:
    UseComm = True

if mpi.UseComm:
    from mpi4py import MPI


if __name__ == "__main__":
    nelems = 10

    if mpi.UseComm:
        comm = MPI.COMM_WORLD
        adios = adios2.ADIOS(comm)
        rank = comm.Get_rank()
        size = comm.Get_size()
    else:
        adios = adios2.ADIOS()
        rank = 0
        size = 1
        comm = None


    #@effis-init comm=comm

    # Test scalars
    if rank == 0:
        KnownInt = np.array([666])
        RandomInt = np.random.randint(0, 1000, size=1)

    # Test arrays
    KnownInts = np.arange(0, nelems, dtype=np.int64)
    RandomInts = np.random.randint(0, 1000, size=nelems, dtype=np.int64)
    RandomInts2 = np.random.randint(0, 1000, size=nelems, dtype=np.int32)


    #@effis-begin engine--->"Jabberwocky"
    io = adios.DeclareIO("Jabberwocky")

    GlobalDims = [size * nelems]
    Offsets = [rank * nelems]
    LocalDims = [nelems]
    vKnownInts  = io.DefineVariable("KnownInts",  KnownInts,  GlobalDims, Offsets, LocalDims)
    vRandomInts = io.DefineVariable("RandomInts", RandomInts, GlobalDims, Offsets, LocalDims)
    vRandomInts2 = io.DefineVariable("RandomInts2", RandomInts2, GlobalDims, Offsets, LocalDims)
    if rank == 0:
        io.DefineVariable("KnownInt",  KnownInt,  [], [], [])
        vRandomInt = io.DefineVariable("RandomInt", RandomInt, [], [], [])


    # Open
    if mpi.UseComm:
        engine = io.Open("Jabberwocky.bp", adios2.Mode.Write, comm)
    else:
        engine = io.Open("Jabberwocky.bp", adios2.Mode.Write)


    for i in range(30):

        RandomInts = np.random.randint(0, 1000, size=nelems, dtype=np.int64)
        RandomInts2 = np.random.randint(0, 1000, size=nelems, dtype=np.int64)
        #@effis-timestep physical=i*0.01, number=i

        if i % 5 == 0:
            engine.BeginStep()
            engine.Put(vKnownInts,  KnownInts)
            engine.Put(vRandomInts, RandomInts)
            engine.Put(vRandomInts2, RandomInts2)
            engine.EndStep()

        print('Increment:', i); sys.stdout.flush()
        time.sleep(2)

    engine.Close()
    #@effis-end

    #@effis-finalize

