#!/usr/bin/env python3

import time
import socket
import argparse
import os
import sys

import effis.runtime
import effis.composition


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--nothing", "-n", help="Nothing", default=None)
    args = parser.parse_args()

    hostname = socket.gethostname()

    if args.nothing is not None:
        print(args.nothing, hostname); sys.stdout.flush()

    SleepExample = os.path.join(effis.composition.ExamplesPath, "NodeShare-Hostname-Sleep", "HostnameSleep.py")

    """
    runner = effis.runtime.SimpleRunner(
        Name="SleepExample",
        Ranks=2,
        RanksPerNode=2,
        CoresPerRank=1,
        GPUsPerRank=0,
        MPIRunnerArguments="--threads-per-core=1",
    )
    runner += effis.runtime.SimpleJobStep(Filepath=SleepExample, CommandLineArguments="--SleepTime=20", Name="SubTest-01")
    runner += effis.runtime.SimpleJobStep(Filepath=SleepExample, CommandLineArguments="--SleepTime=20", Name="SubTest-02")
    runner += effis.runtime.SimpleJobStep(Filepath=SleepExample, CommandLineArguments="--SleepTime=20", Name="SubTest-03")
    runner.Start()
    runner.Wait()
    """

    """
    job1 = effis.runtime.EffisJobStep(
        Filepath=SleepExample,
        Ranks=2, RanksPerNode=2, CoresPerRank=1, GPUsPerRank=0, Name="SubTest-01",
        MPIRunnerArguments="--threads-per-core=1",
        CommandLineArguments="--SleepTime=20",
    )
    job2 = effis.runtime.EffisJobStep(
        Filepath=SleepExample,
        Ranks=2, RanksPerNode=2, CoresPerRank=1, GPUsPerRank=0, Name="SubTest-02",
        MPIRunnerArguments="--threads-per-core=1",
        CommandLineArguments="--SleepTime=20",
    )
    job3 = effis.runtime.EffisJobStep(
        Filepath=SleepExample,
        Ranks=2, RanksPerNode=2, CoresPerRank=1, GPUsPerRank=0, Name="SubTest-03",
        MPIRunnerArguments="--threads-per-core=1",
        CommandLineArguments="--SleepTime=20",
    )
    job1.wait()
    job2.wait()
    job3.wait()
    """

    """
    jobs = []
    for i in range(5):
        job = effis.runtime.EffisJobStep(
            Filepath=SleepExample,
            Ranks=3, RanksPerNode=3, CoresPerRank=7, GPUsPerRank=1, Name="SubTest-{0}".format(i+1),
            CommandLineArguments="--SleepTime=60",
        )
        #MPIRunnerArguments=["--threads-per-core=1", "--exact", "--ntasks-per-node=1", "--gpu-bind=closest"],
        jobs += [job]
        
    for job in jobs:
        job.wait()
    """
        

    jobs = []
    Runner = effis.runtime.EffisJobRunner()

    for i in range(5):
        job = effis.runtime.EffisSimpleJobStep(
            Filepath=SleepExample,
            Ranks=3, RanksPerNode=3, CoresPerRank=7, GPUsPerRank=1, Name="SubTest-{0}".format(i+1),
            CommandLineArguments="--SleepTime=60",
        )
        job, log = Runner.JobStep(job)
        jobs += [job]
        
    for job in jobs:
        job.wait()


