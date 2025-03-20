#!/usr/bin/env python3

import effis.composition
import t3d.trinity_lib

import argparse
import os
import re
import shutil


if __name__ == "__main__":

    # Try to automatically find what system we're on
    runner = effis.composition.Workflow.DetectRunnerInfo()


    # Add arguments to configure the composistion setup from the command line
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--indir", help="Path to top parent directory from T3D simulation", required=True, type=str)
    parser.add_argument("-r", "--rundir", help="Path to  run directory", required=True, type=str)

    args = parser.parse_args()

    configname = "test-w7x-gx"
    infile = os.path.join(args.indir, "{0}.bp".format(configname))
    if not os.path.exists(infile):
        effis.composition.EffisLogger.RaiseError(FileExistsError, "Required file {0} not found".format(infile))


    # The "Top Level" entity to configure EFFIS is a Workflow() object
    MyWorkflow = effis.composition.Workflow(
        Runner=None,            # Don't use scheduler, don't need it
        Directory=args.rundir,  # Where we'll run
    )

    """
    # Run a T3D analysis plotter (that installs with T3D and would run post-hoc)
    plot = MyWorkflow.Application(
        cmd="t3d-plot",
        Name="plot",
        Runner=None,
    )
    plot.Input += effis.composition.Input(infile, link=True)
    plot.CommandLineArguments += [
        os.path.basename(infile),
        "--grid",
        "--savefig",
        "-p", "density", "temperature", "pressure", "heat_flux", "particle_flux", "flux",
    ]
    #plot.DependsOn += Simulation
    """

    # This runs a utility that install with EFFIS which converts NetCDF files to ADIOS files
    """
    nc2bp = MyWorkflow.Application(
        cmd="effis-nc2bp",
        Name="nc2bp",
        Runner=None,
    )
    nc2bp.CommandLineArguments += ["--directory", MyWorkflow.Directory]
    nc2bp.DependsOn += Simulation
    """

    # This is an EFFIS shim layer converter for GX, which adds schema (and saves in .bp)
    gx_omas = MyWorkflow.Application(
        cmd="effis-omas-gx",
        Name="gx_omas",
        Runner=None,
    )
    gx_omas.CommandLineArguments += ["--directory", os.path.abspath(args.indir)]
    #gx_omas.DependsOn += Simulation

    # This is an EFFIS shim layer converter for VMEC, which adds schema (and saves in .bp)
    geofile = "wout_w7x.nc"
    vmec_omas = MyWorkflow.Application(
        cmd="effis-omas-vmec",
        Name="vmec_omas",
        Runner=None,
        CommandLineArguments=["--filename", os.path.join(os.path.abspath(args.indir), geofile)]
    )

    # Seting .Campaign adds .bp output to an ADIOS campaign
    MyWorkflow.Input += effis.composition.Input(os.path.abspath(args.indir), link=True)
    MyWorkflow.Campaign = os.path.basename(MyWorkflow.Directory)
    MyWorkflow.Campaign.SchemaOnly = True  # Only add things in the schema to the campaign file

    # Create() will copy all the input to run directories
    MyWorkflow.Create()

    # Submit() will submit/run
    MyWorkflow.Submit()

