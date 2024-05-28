#!/usr/bin/env python3

import filelock
import argparse
import json
import subprocess
import os
import sys
from mpi4py import MPI


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--queuefile", "-q", help="Queue file", required=True, type=str)
    parser.add_argument("--setsize", "-s", help="Number of ranks for same job step", required=True, type=int)
    args = parser.parse_args()
    step = None

    comm_world = MPI.COMM_WORLD
    world_rank = comm_world.Get_rank()
    group = world_rank // args.setsize
    grouprank = world_rank % args.setsize
    comm = comm_world.Split(group, grouprank)

    while True:

        step = None

        if grouprank == 0:
            lock = filelock.SoftFileLock("{0}.lock".format(args.queuefile))
            with lock:
                with open(args.queuefile, "r") as infile:
                    queue = json.load(infile)

                if len(queue) > 0:
                    step = queue[0]
                    if len(queue) == 1:
                        queue = []
                    else:
                        queue = queue[1:]
                    with open(args.queuefile, "w", encoding='utf-8') as outfile:
                        json.dump(queue, outfile, ensure_ascii=False, indent=4)

                    print("group: {0}, running: {1}".format(group, ' '.join(step['cmd']))); sys.stdout.flush()
                    #print(os.environ); sys.stdout.flush()
                else:
                    print("group: {0}, Nothing to do... Exiting.".format(group)); sys.stdout.flush()

        step = comm.bcast(step, root=0)
        if step is None:
            break


        # Set custom environment requested by user
        restore = {}
        step['env']['PMI_RANK'] = "{0}".format(grouprank)
        step['env']['PMI_SIZE'] = "{0}".format(args.setsize)

        step['env']['PMI_LOCAL_RANK'] = "{0}".format(grouprank)
        step['env']['PMI_LOCAL_SIZE'] = "{0}".format(args.setsize)
        step['env']['PMI_UNIVERSE_SIZE'] = "{0}".format(args.setsize)

        step['env']['PALS_RANKID'] = "{0}".format(grouprank)
        step['env']['PALS_LOCAL_RANKID'] = "{0}".format(grouprank)

        step['env']['SLURM_NPROCS'] = "{0}".format(args.setsize)
        step['env']['SLURM_NTASKS'] = "{0}".format(args.setsize)
        step['env']['SLURM_TASKS_PER_NODE'] = "{0}".format(args.setsize)
        step['env']['SLURM_STEP_NUM_TASKS'] = "{0}".format(args.setsize)
        step['env']['SLURM_STEP_TASKS_PER_NODE'] = "{0}".format(args.setsize)
        step['env']['SLURM_JOB_CPUS_PER_NODE'] =  '2'

        for var in step['env']:
            if var in os.environ:
                restore[var] = os.environ[var]
            os.environ[var] = step['env'][var]

        # Run here
        runlog = "{0}.log".format(step['name'])
        with open(runlog, 'w') as runlog:
            comm.Barrier()
            print("group: {0}, rank: {1}, running: {2}".format(group, grouprank, ' '.join(step['cmd']))); sys.stdout.flush()
            print("group: {0}, rank: {1}, env: {2}".format(group, grouprank, os.environ)); sys.stdout.flush()
            #phandle = subprocess.run(step['cmd'], stdout=runlog, stderr=runlog,)
            phandle = subprocess.run(step['cmd'], env=os.environ)
            print("group: {0}, rank: {1}, returned".format(group, grouprank)); sys.stdout.flush()
            #comm.Spawn(sys.executable, args=step['cmd'], maxprocs=args.setsize, root=0)
            #comm.Wait()
            comm.Barrier()

        # Reset environment back to before
        for var in restore:
            os.environ[var] = restore[var]

