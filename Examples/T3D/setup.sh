
module load gsl
module load gcc
module load hdf5
module load netcdf-c
module load netlib-lapack

NVHPC=/sw/summit/nvhpc_sdk/Linux_ppc64le/23.9
CUDA=/sw/summit/cuda/11.0.3/targets/ppc64le-linux
NVHPC_MATH=$NVHPC/math_libs/11.0/targets/ppc64le-linux
NVHPC_NCCL=$NVHPC/comm_libs/11.0/nccl
export LD_LIBRARY_PATH=$CUDA/lib:$NVHPC_MATH/lib:$NVHPC_NCCL/lib:$LD_LIBRARY_PATH

export PYTHONPATH=$PYTHONPATH:/ccs/home/esuchyta/software/install/summit/adios2-gcc12.1.0-login/lib/python3.11/site-packages
module load libfabric

export GK_SYSTEM=summit
export GX_PATH_PY=/ccs/home/esuchyta/software/src/gx/

#export GX_PATH=/ccs/home/esuchyta/software/src/gx/
#export GX_PATH=/ccs/home/esuchyta/software/build/summit/gx-next
export GX_PATH=/ccs/home/esuchyta/software/build/summit/gx-adios
export LD_LIBRARY_PATH=/ccs/home/esuchyta/software/install/summit/adios2-nvhpc23.9/lib64:$LD_LIBRARY_PATH
