#!/usr/bin/env python3

import omas
import effis.shim

import os
import argparse
import sys
import numpy as np

import adios2
import netCDF4


def nc2bp_omas(filename=None, directory=None):

    if (filename is None) and (directory is None):
        raise ValueError("Must set filename or directory")
    elif (filename is not None) and (directory is not None):
        raise ValueError("Can't set both filename and directory")

    elif filename is not None:
        if not os.path.exists(filename):
            raise ValueError("Given file path does not exist: {0}".format(filename))
        files = [filename]

    elif directory is not None:
        if not os.path.exists(directory):
            raise ValueError("Given directory path does not exist: {0}".format(directory))
        files = effis.composition.workflow.FindExt(directory, ext="out.nc", isdir=False)

    
    for filename in files:

        top = netCDF4.Dataset(filename)
       
        grids = top.groups["Grids"]
        diagnostics = top.groups["Diagnostics"]
        geometry = top.groups["Geometry"]
        inputs = top.groups["Inputs"]
        controls = inputs.groups["Controls"]
        species = inputs.groups["Species"]
        boltzmann = species.groups["Boltzmann"]

        ods = omas.ODS(consistency_check=False)

        ods["gyrokinetics_local.flux_surface.geometric_axis_r_dr_minor"] = geometry["shift"][:]
        ods["gyrokinetics_local.flux_surface.magnetic_shear_r_minor"] = geometry["shat"][:]
        ods["gyrokinetics_local.normalizing_quantities.r"] = geometry["rmaj"][:]
        # [Geometry]: akappa
        # [Geometry]: akappri
        # [Geometry]: betaprim
        # [Geometry]: qinp
        # [Geometry]: rhoc

        ods["gyrokinetics_local.species_all.beta_reference"] = inputs["beta"][:]

        ods["gyrokinetics_local.linear"] = controls["nonlinear_mode"][:]

        for i in range(len(species['z'][:])):
            effis.shim.EffisLogger.Debug("z shape: {0}".format(species['z'].shape))
            ods["gyrokinetics_local.species.{0}.charge_norm".format(i)] = species['z'][i]
            ods["gyrokinetics_local.species.{0}.mass_norm".format(i)] = species['m'][i]
            ods["gyrokinetics_local.species.{0}.density_norm".format(i)] = species['n0'][i]
            ods["gyrokinetics_local.species.{0}.temperature_norm".format(i)] = species['T0'][i]
            ods["gyrokinetics_local.species.{0}.temperature_log_gradient_norm".format(i)] = species['T0_prime'][i]
            # [Species]: fprim
            # [Species]: vnewk 

            ods["gyrokinetics_local.non_linear.fluxes_1d_rotating_frame.energy_phi_potential"] = np.sum(diagnostics["HeatFluxES_st"][-1, :])
            ods["gyrokinetics_local.non_linear.fluxes_1d_rotating_frame.energy_a_field_parallel"] = np.sum(diagnostics["HeatFluxApar_st"][-1, :])
            ods["gyrokinetics_local.non_linear.fluxes_1d_rotating_frame.energy_b_field_parallel"] = np.sum(diagnostics["HeatFluxBpar_st"][-1, :])
            # [Fluxes]: pflux


        if (boltzmann['Boltzmann_type_dum'].value == "electron") and (boltzmann['add_Boltzmann_species'][:] == 1):
            ods["gyrokinetics_local.model.adiabatic_electrons"] = boltzmann['add_Boltzmann_species'][:]

        ods["gyrokinetics_local.non_linear.binormal_wavevector_norm"] = grids["kx"][:]
        ods["gyrokinetics_local.non_linear.radial_wavevector_norm"] = grids["ky"][:]
        ods["gyrokinetics_local.non_linear.angle_pol"] = grids["theta"][:]


        bppath = os.path.join(os.path.dirname(filename), os.path.splitext(os.path.basename(filename))[0])

        #omas.save_omas_adios(ods, "ODS-GX-01")
        effis.shim.save_omas_adios(ods, bppath)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename", help="Path to netCDF file", type=str, default=None)
    parser.add_argument("-d", "--directory", help="Directory with files", type=str, default=None)
    parser.add_argument("-g", "--debug", help="Use debug prints", action="store_true")
    args = parser.parse_args()

    if args.debug:
        effis.shim.EffisLogger.SetDebug()

    nc2bp_omas(filename=args.filename, directory=args.directory)



if __name__ == "__main__":

    main()

