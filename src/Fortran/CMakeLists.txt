add_definitions(${fortran_free_flag})

if(USE_MPI)
	if(ADIOS2_VERSION LESS 2.4.0)
		add_definitions(-DADIOS2_OLD_STEP)
	endif()
	add_definitions(-DUSE_MPI)
endif()

if(FINE_TIME)
	add_definitions(-DFINE_TIME)
endif()

set(module_objects 
	${CMAKE_CURRENT_SOURCE_DIR}/kittie.F90
	${CMAKE_CURRENT_SOURCE_DIR}/kittie_internal.F90
)

set_source_files_properties(
	${CMAKE_CURRENT_SOURCE_DIR}/kittie.F90
	PROPERTIES
		OBJECT_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/kittie_internal.F90
)

add_library(kittie_f ${module_objects})
target_link_libraries(kittie_f PRIVATE adios2::adios2_f)
set_property(TARGET kittie_f PROPERTY EXPORT_NAME fortran)

target_include_directories(kittie_f PUBLIC
	$<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}>
	$<INSTALL_INTERFACE:${CMAKE_INSTALL_PREFIX}/include>
)

install(
	DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/
	DESTINATION ${CMAKE_INSTALL_PREFIX}/include
	FILES_MATCHING PATTERN "kittie*.mod" PATTERN "CMakeFiles" EXCLUDE
)

install(
	TARGETS kittie_f
	EXPORT effis-targets
	DESTINATION ${CMAKE_INSTALL_PREFIX}/lib
)

