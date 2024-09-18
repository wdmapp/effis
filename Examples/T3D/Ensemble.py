#!/usr/bin/env python3

import effis.composition
import t3d.trinity_lib

import argparse
import os
import re


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--outdir", help="Path to top parent directory for run directory", required=True, type=str)
    args = parser.parse_args()

    t3dir = os.path.dirname(t3d.trinity_lib.__file__)
    setupdir = os.path.join(os.path.dirname(t3dir), "tests", "regression")
    datadir = os.path.join(os.path.dirname(t3dir), "tests", "data")
    configname = "test-w7x-relu"


    runner = effis.composition.Workflow.DetectRunnerInfo()

    MyWorkflow = effis.composition.Workflow(
        Runner=runner,
        Directory=args.outdir,
    )
    MyWorkflow.GroupMax['t3d'] = 2


    for i in range(10):

        Simulation = MyWorkflow.Application(
            cmd="t3d",
            Name="T3D-{0:02d}".format(i+1),
            Ranks=1,
            #Runner=None,
            Group='t3d'
        )
        Simulation.CommandLineArguments += [
            "{0}.in".format(configname),
            "--log", "{0}.out".format(configname),
        ]

        Simulation.Input += effis.composition.Input(os.path.join(setupdir, "{0}.in".format(configname)))
        Simulation.Input += effis.composition.Input(os.path.join(datadir, "wout_w7x.nc"), link=True)
       
        """
        if i > 0:
            Simulation.DependsOn += MyWorkflow.Applications[-3]
        """

        plot = MyWorkflow.Application(
            cmd="t3d-plot",
            Name="plot-{0:02d}".format(i+1),
            Runner=None,
        )
        plot.CommandLineArguments += [
            os.path.relpath(os.path.join(Simulation.Directory, "{0}.bp".format(configname)), start=plot.Directory),
            "--grid",
            "--savefig",
            "-p", "density", "temperature", "pressure", "heat_flux", "particle_flux", "flux",
        ]
        plot.DependsOn += Simulation


    MyWorkflow.Create()


    for i, Simulation in enumerate(MyWorkflow.Applications):

        if Simulation.Name.find("plot") != -1:
            continue

        # Rewrite a few things in the config file
        with open(os.path.join(Simulation.Directory, "{0}.in".format(configname)), 'r') as infile:
            config = infile.read()
        config = re.compile(r"geo_file\s*=\s*.*", re.MULTILINE).sub('geo_file = "wout_w7x.nc"', config)

        core = 0.35 + i*0.01
        edge = 0.29 + i*0.01
        config = re.compile(
            r"density = {core = 0.35, edge = 0.29, alpha=1, evolve = false}", re.MULTILINE).sub(
                "density = {{core = {0}, edge = {1}, alpha=1, evolve = false}}".format(core, edge), config
            )

        with open(os.path.join(Simulation.Directory, "{0}.in".format(configname)), 'w') as outfile:
            outfile.write(config)

