#!/usr/bin/env python3

import sys
import os

#print("started"); sys.stdout.flush()
#print(os.environ); sys.stdout.flush()

import time
from datetime import datetime
import socket
import argparse
import multiprocessing
import psutil
import subprocess

#print("MPI"); sys.stdout.flush()
from mpi4py import MPI
#print("MPI done"); sys.stdout.flush()

#import filelock
import effis.composition


if __name__ == "__main__":

    #print("comm"); sys.stdout.flush()
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    #print("comm done"); sys.stdout.flush()

    start = datetime.now()
    parser = argparse.ArgumentParser()
    parser.add_argument("--SleepTime", "-t", help="Time to sleep", type=int, default=None)
    args = parser.parse_args()

    hostname = socket.gethostname()
    print("host: {0}, rank: {1}, cpu_num: {2}".format(hostname, rank, psutil.Process().cpu_num())); sys.stdout.flush()
   
    if args.SleepTime is not None:

        filename = "TestFile01.txt"
        if rank == 0:
            """
            lock = filelock.SoftFileLock("{0}.lock".format(filename))
            with lock:
                with open(filename, "r") as infile:
                    txt = infile.read().strip()
                time.sleep(args.SleepTime)
            """
            time.sleep(args.SleepTime)
            print("host: {0}, rank: {1}, cpu_num: {2}... slept with lock: {3}".format(hostname, rank, psutil.Process().cpu_num(), "ABC")); sys.stdout.flush()
        
        """
        SleepExample = os.path.join(effis.composition.ExamplesPath, "NodeShare-Hostname-Sleep", "HostnameSleep.py")
        runargs = [SleepExample]
        a = datetime.now()
        subprocess.run(runargs)  # For some reason this is collective
        b = datetime.now()
        diff = (b - a).total_seconds()
        print("host: {0}, rank: {1}, cpu_num: {2}... subprocess time: {3} s".format(hostname, rank, psutil.Process().cpu_num(), diff)); sys.stdout.flush()
        """

    end = datetime.now()
    diff = (end - start).total_seconds()
    print("host: {0}, rank: {1}, cpu_num: {2}... total time: {3} s".format(hostname, rank, psutil.Process().cpu_num(), diff)); sys.stdout.flush()

