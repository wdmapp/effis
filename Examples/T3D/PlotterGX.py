#!/usr/bin/env python3

import argparse
import adios2
import sys
import os
import effis.runtime

# heat_flux.py
# lh-spectra.py
# plot-Phi2-kx.py 
# plot-Phi2-ky.py
# plot-Pky.py
# plot-Qky.py

# plot-Phi2-zonal-kx.py ... just not using for now
# plot-Phi2-ky-vs-time.py ... very hard to read with so much going on

# (particle_flux.py) ... all 0's for T3D run
# (plot-Gamky.py) ... same as particle_flux.py ?
# plot_geometry.py ... uses different files


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        description="Read ADIOS file for job progress and plot GX results as available."
    )
    parser.add_argument("-f", "--filename", required=True, default=None, type=str, help="Progress file (.bp)")
    parser.add_argument("-x", "--xml", required=False, default=None, type=str, help="ADIOS XML configuration")
    args = parser.parse_args()

    thisdir = os.getcwd()
    EffisRunner = effis.runtime.EffisJobRunner(base=thisdir)

    if "GX_PATH_PY" in os.environ:
        gxpost = os.path.join(os.environ["GX_PATH_PY"], "post_processing")
    else:
        gxpost = os.path.join(os.environ["GX_PATH"], "post_processing")

    if args.xml is not None:
        adios = adios2.Adios(args.xml)
    else:
        adios = adios2.Adios()

    pids = []
    io = adios.declare_io("Done")
    with adios2.Stream(io, args.filename, "r") as stream:
        for _ in stream.steps():
            filename = stream.read("filename")
            print(stream.current_step(), filename); sys.stdout.flush()

            index = 0
            remaning = len(pids)
            for i in range(remaning):
                pid = pids[index]
                if pid.poll() is not None:
                    del pids[index]
                else:
                    index += 1
    
            dirname = os.path.basename(filename[:-3])
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            os.chdir(dirname)

            for aname in [
                "heat_flux.py",
                "lh-spectra.py",
                "plot-Phi2-kx.py",
                "plot-Phi2-ky.py",
                "plot-Pky.py",
                "plot-Qky.py",
            ]:
                JobStep = EffisRunner.SimpleJobStep(
                    Name="{0}".format(aname[:-3],),
                    Filepath="python3", CommandLineArguments=[os.path.join(gxpost, aname), filename],
                    Ranks=1, CoresPerRank=1, GPUsPerRank=0,
                    )
                pid, logname = EffisRunner.JobStep(JobStep)
                pids += [pid]

            os.chdir("..")

    for pid in pids:
        pid.wait()

