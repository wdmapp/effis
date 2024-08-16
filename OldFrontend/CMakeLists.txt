# I don't really know what version is actually needed but 3.0 seems sensible -- certainly using CMake-3 syntax
cmake_minimum_required(VERSION 3.12.0)
project(EFFIS VERSION 0.1)
enable_language(Fortran)

# Let the user tell us if they want MPI. MPI is ON by default.
# Installation will fail if you don't give the MPI compiler wrappers and try to use MPI
set(USE_MPI ON CACHE STRING "Use MPI")
set(FINE_TIME OFF CACHE STRING "Finer timing")
set_property(CACHE USE_MPI PROPERTY STRINGS "ON;TRUE;OFF;FALSE")
set_property(CACHE FINE_TIME PROPERTY STRINGS "ON;TRUE;OFF;FALSE")

find_package(ADIOS2 REQUIRED)
find_package(yaml-cpp REQUIRED)
find_package(Python REQUIRED)


# Test Fortran compiler
include(CheckFortranCompilerFlag)
check_fortran_compiler_flag("-ffree-line-length-none" exists_gnu)
if(exists_gnu)
	set(fortran_free_flag "-ffree-line-length-none")
#elseif(exists_pgi)
#	set(fortran_free_flag "
endif()

function(preprocess)
	execute_process(COMMAND ${Python_EXECUTABLE} ${PROJECT_SOURCE_DIR}/util/effis-cpp.py repo ${CMAKE_CURRENT_SOURCE_DIR} --tree-output=${CMAKE_CURRENT_BINARY_DIR})
endfunction()

# Add all the build files
add_subdirectory(src)
add_subdirectory(config)
add_subdirectory(util)
add_subdirectory(plot)
add_subdirectory(examples)

install(
	EXPORT effis-targets
	FILE effisTargets.cmake
	NAMESPACE effis::
	DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/cmake/effis
)

include (CMakePackageConfigHelpers)
configure_package_config_file(
	${CMAKE_CURRENT_LIST_DIR}/effisConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/effisConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/cmake/effis
)
install(
	FILES ${CMAKE_CURRENT_BINARY_DIR}/effisConfig.cmake
	DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/cmake/effis
)
