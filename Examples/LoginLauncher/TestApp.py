#!/usr/bin/env python3

import time
import socket
import argparse
import os

import effis.runtime
import effis.composition


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--nothing", "-n", help="Nothing", default=None)
    args = parser.parse_args()

    hostname = socket.gethostname()

    if args.nothing is not None:
        print(args.nothing, hostname)

    SleepExample = os.path.join(effis.composition.ExamplesPath, "NodeShare-Hostname-Sleep", "HostnameSleep.py")

    job1 = effis.runtime.JobStep(
        Filepath=SleepExample,
        Ranks=1, RanksPerNode=1, CoresPerRank=1, GPUsPerRank=0, Name="SubTest-01",
        MPIRunnerArguments="--threads-per-core=1",
        CommandLineArguments="--SleepTime=20",
    )
    job2 = effis.runtime.JobStep(
        Filepath=SleepExample,
        Ranks=1, RanksPerNode=1, CoresPerRank=1, GPUsPerRank=0, Name="SubTest-02",
        MPIRunnerArguments="--threads-per-core=1",
        CommandLineArguments="--SleepTime=20",
    )
    job3 = effis.runtime.JobStep(
        Filepath=SleepExample,
        Ranks=1, RanksPerNode=1, CoresPerRank=1, GPUsPerRank=0, Name="SubTest-03",
        MPIRunnerArguments="--threads-per-core=1",
        CommandLineArguments="--SleepTime=20",
    )
    job1.wait()
    job2.wait()
    job3.wait()
