#!/bin/sh

module load gsl
module load libfabric

module load gcc/6.5.0
module load cuda/10.2.89
module load nccl/2.9.9-1-cuda10.2
export CUDA_VERSION=10.2
export CUTENSOR_ROOT=/ccs/home/esuchyta/software/install/andes/libcutensor-linux-x86_64-1.7.0.1-archive
export NCCL_ROOT=${OLCF_NCCL_ROOT}
export LD_LIBRARY_PATH=${CUTENSOR_ROOT}/lib/${CUDA_VERSION}:$LD_LIBRARY_PATH

export OLCF_HDF5_ROOT=/ccs/home/esuchyta/software/install/andes/hdf5-1.14.5
export OLCF_NETCDF_C_ROOT=/ccs/home/esuchyta/software/install/andes/netdf-c-4.9.2
export LD_LIBRARY_PATH=${OLCF_NETCDF_C_ROOT}/lib:${OLCF_HDF5_ROOT}/lib:$LD_LIBRARY_PATH

# My ADIOS Python is built with gcc/9.3.0
export LD_LIBRARY_PATH=/sw/andes/gcc/9.3.0/lib64:$LD_LIBRARY_PATH

export GK_SYSTEM=andes
