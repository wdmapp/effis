# I don't really know what version is actually needed but 3.0 seems sensible -- certainly using CMake-3 syntax
cmake_minimum_required(VERSION 3.0)
project(KITTIE VERSION 0.1)
enable_language(Fortran)

# Custom CMake package modules
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${PROJECT_SOURCE_DIR}/cmake_modules)


# Let the user tell us if they want MPI. MPI is ON by default.
# Installation will fail if you don't give the MPI compiler wrappers and try to use MPI
set(USE_MPI ON CACHE STRING "Use MPI")
set(FINE_TIME OFF CACHE STRING "Finer timing")
set(PYTHON_PREFIX ON CACHE STRING "Use MPI")
set_property(CACHE USE_MPI PROPERTY STRINGS "ON;TRUE;OFF;FALSE")
set_property(CACHE FINE_TIME PROPERTY STRINGS "ON;TRUE;OFF;FALSE")
set_property(CACHE PYTHON_PREFIX PROPERTY STRINGS "ON;TRUE;OFF;FALSE")

# Find ADIOS-2
find_package(ADIOS2 REQUIRED)
#find_package(Yamlcpp REQUIRED)
find_package(yaml-cpp REQUIRED)

#find_package(PythonInterp REQUIRED)
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
	find_package(PythonInterp REQUIRED)
else()
	find_package(Python REQUIRED)
endif()


# Test Fortran compiler
include(CheckFortranCompilerFlag)
check_fortran_compiler_flag("-ffree-line-length-none" exists_gnu)
if(exists_gnu)
	set(fortran_free_flag "-ffree-line-length-none")
#elseif(exists_pgi)
#	set(fortran_free_flag "
endif()


# Add all the build files
add_subdirectory(src)
add_subdirectory(config)
add_subdirectory(util)
add_subdirectory(plot)
add_subdirectory(examples)

message(STATUS "prefix: ${CMAKE_INSTALL_PREFIX}")
