#!/bin/sh
export CUDA_VERSION=11.7

module load PrgEnv-gnu
module load gcc/11.2.0
module load nvhpc-mixed/22.7
module load cudatoolkit/$CUDA_VERSION
module load cray-hdf5-parallel
module load cray-netcdf-hdf5parallel
module load libfabric

ADIOS=/global/homes/e/esuchyta/software/install/perlmutter/adios2-gcc11.2.0
export LD_LIBRARY_PATH=$ADIOS/lib64:$LD_LIBRARY_PATH
export PYTHONPATH=$PYTHONPATH:$ADIOS/lib/python3.11/site-packages
