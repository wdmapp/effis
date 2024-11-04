module load gsl

module load nvhpc/23.9
module load cuda/11.0.3
module load libfabric
module load netlib-lapack
module load hdf5
module load netcdf-c
export LD_LIBRARY_PATH=/ccs/home/esuchyta/software/install/summit/adios2-nvhpc23.9/lib64:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/sw/summit/gcc/12.1.0-0/lib64:$LD_LIBRARY_PATH
export PYTHONPATH=/ccs/home/esuchyta/software/install/summit/adios2-gcc12.1.0/lib/python3.11/site-packages:$PYTHONPATH

CUDA_VERSION=11.0
CUDA=${CUDA_DIR}/targets/ppc64le-linux
NVHPC_NCCL=${OLCF_NVHPC_ROOT}/comm_libs/${CUDA_VERSION}/nccl
NVHPC_MATH=${OLCF_NVHPC_ROOT}/math_libs/${CUDA_VERSION}/targets/ppc64le-linux
export LD_LIBRARY_PATH=${NVHPC_MATH}/lib:${NVHPC_NCCL}/lib:${CUDA}/lib:$LD_LIBRARY_PATH

export GK_SYSTEM=summit
