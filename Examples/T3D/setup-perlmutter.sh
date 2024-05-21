export CUDA_VERSION=11.7

module load PrgEnv-gnu
module load gcc/11.2.0
module load nvhpc-mixed/22.7
module load cudatoolkit/$CUDA_VERSION
module load cray-hdf5-parallel
module load cray-netcdf-hdf5parallel
module load libfabric

export GK_SYSTEM=perlmutter
export GX_PATH=$HOME/software/build/perlmutter/gx-adios
#export GX_PATH_PY=/ccs/home/esuchyta/software/src/gx/

ADIOS=/global/homes/e/esuchyta/software/install/perlmutter/adios2-gcc11.2.0
export LD_LIBRARY_PATH=$ADIOS/lib64:$LD_LIBRARY_PATH
export PYTHONPATH=$PYTHONPATH:$ADIOS/lib/python3.11/site-packages

