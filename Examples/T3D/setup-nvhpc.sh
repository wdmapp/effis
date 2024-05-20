module load gsl

module load gcc
module load hdf5
module load netcdf-c
module load netlib-lapack
NVHPC=/sw/summit/nvhpc_sdk/Linux_ppc64le/23.9
CUDA=/sw/summit/cuda/12.2.0/targets/ppc64le-linux
#NVHPC_MATH=$NVHPC/math_libs/12.2/targets/ppc64le-linux
NVHPC_MATH=/sw/summit/nvhpc_sdk/Linux_ppc64le/22.9/math_libs/11.7/targets/ppc64le-linux
NVHPC_NCCL=$NVHPC/comm_libs/12.2/nccl
export LD_LIBRARY_PATH=$CUDA/lib:$NVHPC_MATH/lib:$NVHPC_NCCL/lib:$LD_LIBRARY_PATH


#module load nvhpc/23.9
#module load netlib-lapack
#HDF5_ROOT=/sw/summit/spack-envs/summit-plus/opt/gcc-12.1.0/hdf5-1.14.3-qkrpzuwj32v6awqw5rgv5g5kyurnt563
#NETCDF_ROOT=/sw/summit/spack-envs/summit-plus/opt/gcc-12.1.0/netcdf-c-4.9.2-ncc363o37f42yqfwhwh4g7phg6epjylc
##export LD_LIBRARY_PATH=$NETCDF_ROOT/lib64:$HDF5_ROOT/lib:/sw/summit/nvhpc_sdk/Linux_ppc64le/22.9/math_libs/11.7/targets/ppc64le-linux/lib:$LD_LIBRARY_PATH
#export LD_LIBRARY_PATH=$NETCDF_ROOT/lib64:$HDF5_ROOT/lib:$LD_LIBRARY_PATH
#export LD_LIBRARY_PATH=/sw/summit/gcc/12.2.0-0/lib64:/sw/summit/gcc/12.2.0-0/libexec/gcc/powerpc64le-unknown-linux-gnu/12.2.0:/sw/summit/gcc/12.2.0-0/lib/gcc/powerpc64le-unknown-linux-gnu/12.2.0:/sw/summit/gcc/:$LD_LIBRARY_PATH


module load libfabric
export PYTHONPATH=$PYTHONPATH:/ccs/home/esuchyta/software/build/summit/adios2-gcc12.1.0-login/lib/python3.11/site-packages
export GK_SYSTEM=summit
export GX_PATH_PY=/ccs/home/esuchyta/software/src/gx/
export GX_PATH=/ccs/home/esuchyta/software/build/summit/gx-next
#export GX_PATH=/ccs/home/esuchyta/software/src/gx/
