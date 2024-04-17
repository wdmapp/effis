#!/usr/bin/env python3

import os
import sys
import time
from datetime import datetime
import socket
import argparse
import multiprocessing
import psutil
import subprocess

import filelock
import effis.composition


if __name__ == "__main__":

    start = datetime.now()
    parser = argparse.ArgumentParser()
    parser.add_argument("--SleepTime", "-t", help="Time to sleep", type=int, default=None)
    args = parser.parse_args()

    hostname = socket.gethostname()
    print(
        hostname,
        multiprocessing.cpu_count(),
        os.cpu_count(),
        psutil.Process().cpu_num()
    ); sys.stdout.flush()
   
    if args.SleepTime is not None:
        filename = "TestFile01.txt"
        lock = filelock.SoftFileLock("{0}.lock".format(filename))
        with lock:
            with open(filename, "r") as infile:
                txt = infile.read()
            time.sleep(args.SleepTime)
            print(txt); sys.stdout.flush()
            
        SleepExample = os.path.join(effis.composition.ExamplesPath, "NodeShare-Hostname-Sleep", "HostnameSleep.py")
        runargs = [SleepExample]
        subprocess.run(runargs)

    end = datetime.now()
    diff = (end - start).total_seconds()
    print("Time: {0} s".format(diff))
