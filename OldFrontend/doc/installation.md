# Installation

## Dependencies 

The dependencies for EFFIS itself are rather light.
(Whereas the dependencies for the science codes one might run with EFFIS could be rather extensive.)

* [ADIOS-2](https://github.com/ornladios/ADIOS2) 

    EFFIS uses/requires MPI if ADIOS does, and does not use MPI if ADIOS does not.

* [yaml-cpp](https://github.com/jbeder/yaml-cpp/)
 
	This is actually only used from the C++ code, but at the moment, CMake requires finding yaml-cpp regardless if C++ is needed or not.

* [Python](https://www.python.org/)

    See notes on below.

A full installation of EFFIS includes the python features, which require Python 3 because Cheetah requires Python 3. 
In EFFIS, you only need Cheetah for composing the jobs, which runs on the login nodes. 
So it is fine to have separate EFFIS libraries on the login and compute nodes, if one is not running Python 3 on the compute nodes.

* [Cheetah](https://github.com/CODARcode/cheetah/tree/dev)

    This is the `dev` branch, which is the main one (not `master` for irrelevant reason).

* [NumPy](https://numpy.org/)

    Need job composition and running EFFIS python apps/services (because ADIOS needs it).

* [PyYAML](https://pyyaml.org/)

    Need job composition and running EFFIS python apps/services.

* [Matplotlib](https://matplotlib.org/)

    Need for plotting services

Note: The above packages are Python modules. Currently, EFFIS doesn't actually check for them at installation time.


## EFFIS

EFFIS itself is a CMake package. It's customary to build CMake packages out-of-source, in a build directory.
It's easiest to explain the installation variables through an example.
None of the environment variable names are special to the EFFIS installation, they're just used here qualitatively.

```
mkdir build
cd build

cmake \
-DUSE_MPI=ON \
-DCMAKE_INSTALL_PREFIX=$(EFFIS) \
-DCMAKE_PREFIX_PATH=$(ADIOS2);$(PYTHON);$(YAML_CPP) \
-DCMAKE_CXX_COMPILER=mpicxx \
-DCMAKE_Fortran_COMPILER=mpif90 \
../
```

* **USE_MPI**: Turn MPI on or off
* **CMAKE_INSTALL_PREFIX**: Where you want EFFIS to install
* **CMAKE_PREFIX_PATH**: Directories where dependencies are installed

