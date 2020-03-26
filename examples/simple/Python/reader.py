#!/usr/bin/env python

import adios2
import time
import socket

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
    #@effis-end

    if mpi.UseComm:
        #@effis-begin reader_io-->"Jabberwocky"
        reader = reader_io.Open("Jabberwocky.bp", adios2.Mode.Read, comm)
        #@effis-end
    else:
        #@effis-begin reader_io-->"Jabberwocky"
        reader = reader_io.Open("Jabberwocky.bp", adios2.Mode.Read)
        #@effis-end


    #@effis-begin reader--->"Jabberwocky"
    while True:

        status = reader.BeginStep(kittie.Kittie.ReadStepMode, 10.0)

        if status == adios2.StepStatus.NotReady:
            time.sleep(1)
            continue
        elif status != adios2.StepStatus.OK:
            break

        print(reader.CurrentStep())
        reader.EndStep()

    reader.Close()
    #@effis-end

    #@effis-finalize
