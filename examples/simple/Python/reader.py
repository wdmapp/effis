#!/usr/bin/env python3

import adios2
import time
import socket
import sys

class mpi:
    UseComm = True

if mpi.UseComm:
    from mpi4py import MPI


if __name__ == "__main__":

    if mpi.UseComm:
        comm = MPI.COMM_WORLD
        adios = adios2.ADIOS(comm)
    else:
        adios = adios2.ADIOS()
        comm = None

    #@effis-init comm=comm

    #@effis-begin "Jabberwocky"->"Jabberwocky"
    reader_io = ad.DeclareIO("Jabberwocky")

    if mpi.UseComm:
        reader = reader_io.Open("Jabberwocky.bp", adios2.Mode.Read, comm)
    else:
        reader = reader_io.Open("Jabberwocky.bp", adios2.Mode.Read)

    while True:

        status = reader.BeginStep(kittie.Kittie.ReadStepMode, 10.0)

        if status == adios2.StepStatus.NotReady:
            continue
        elif status != adios2.StepStatus.OK:
            break

        print("Found:", reader.CurrentStep()); sys.stdout.flush()
        reader.EndStep()

    reader.Close()
    #@effis-end

    #@effis-finalize
