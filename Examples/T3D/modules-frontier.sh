#!/bin/sh

module load cpe
module load cce
module load rocm/6.3.1

module load cray-hdf5-parallel
module load cray-netcdf-hdf5parallel
module load gsl
module load libfabric

export HIPTENSOR_PATH=/ccs/home/esuchyta/software/build/frontier/hipTensor
export LD_LIBRARY_PATH=$HIPTENSOR_PATH/build/lib:$LD_LIBRARY_PATH

export ADIOS=/ccs/home/esuchyta/software/install/frontier/adios2-gcc12.2.0/
export LD_LIBRARY_PATH=$ADIOS/lib64:$LD_LIBRARY_PATH

# I put this into what pip knows
#export PYTHONPATH=$PYTHONPATH:$ADIOS/lib/python3.11/site-packages

export GK_SYSTEM=frontier

