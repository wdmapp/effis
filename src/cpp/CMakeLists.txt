set(CMAKE_CXX_STANDARD 11)

if(USE_MPI)
	add_definitions(-DUSE_MPI)
	execute_process(COMMAND sed "s/#define NOTHING/#define USE_MPI/g" ${CMAKE_CURRENT_SOURCE_DIR}/kittie.h OUTPUT_FILE ${CMAKE_CURRENT_BINARY_DIR}/kittie.h)
else()
	execute_process(COMMAND sed "s/#define NOTHING/#define NOTHING/g" ${CMAKE_CURRENT_SOURCE_DIR}/kittie.h OUTPUT_FILE ${CMAKE_CURRENT_BINARY_DIR}/kittie.h)
endif()

set(lib_objects ${CMAKE_CURRENT_SOURCE_DIR}/kittie.cpp)
add_library(kittie ${lib_objects})

target_link_libraries(kittie PUBLIC adios2::adios2 PRIVATE yaml-cpp)
target_include_directories(kittie 
	PUBLIC 
	$<BUILD_INTERFACE:${YAML_INCLUDE_DIRS}>
	$<BUILD_INTERFACE:${CMAKE_BINARY_DIR}/src/cpp>
	$<INSTALL_INTERFACE:${YAML_INCLUDE_DIRS}>
	$<INSTALL_INTERFACE:${CMAKE_INSTALL_PREFIX}/include>
)

include(GNUInstallDirs)
set(INSTALL_CONFIGDIR ${CMAKE_INSTALL_LIBDIR}/cmake/kittie)

install(TARGETS kittie 
	EXPORT kittie-targets 
	LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/kittie.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

install(EXPORT kittie-targets
    FILE
        kittieTargets.cmake
    NAMESPACE
        kittie::
    DESTINATION
        ${INSTALL_CONFIGDIR}
)

include (CMakePackageConfigHelpers)
write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/kittieConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY AnyNewerVersion
)

configure_package_config_file(${CMAKE_CURRENT_LIST_DIR}/kittieConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/kittieConfig.cmake
    INSTALL_DESTINATION ${INSTALL_CONFIGDIR}
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/kittieConfig.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/kittieConfigVersion.cmake
    DESTINATION ${INSTALL_CONFIGDIR}
)

export(EXPORT kittie-targets
    FILE ${CMAKE_CURRENT_BINARY_DIR}/kittieUtilsTargets.cmake
    NAMESPACE kittieUtils::)

export(PACKAGE kittie)