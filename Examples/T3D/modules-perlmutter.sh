#!/bin/sh

#export CUDA_VERSION=11.7
#module load PrgEnv-gnu
#module load gcc/11.2.0
#module load nvhpc-mixed/22.7
#module load cudatoolkit/$CUDA_VERSION
#module load cray-hdf5-parallel
#module load cray-netcdf-hdf5parallel
#module load libfabric

#export GK_SYSTEM=perlmutter
module load PrgEnv-gnu/8.5.0
module load nvidia-mixed/24.5
module load cudatoolkit/12.4
module load cray-mpich/8.1.28
module load nccl
module load cray-hdf5-parallel
module load cray-netcdf-hdf5parallel
#module load python

#ADIOS=/global/homes/e/esuchyta/software/install/perlmutter/adios2-gcc11.2.0
#export LD_LIBRARY_PATH=$ADIOS/lib64:$LD_LIBRARY_PATH
#export PYTHONPATH=$PYTHONPATH:$ADIOS/lib/python3.11/site-packages
