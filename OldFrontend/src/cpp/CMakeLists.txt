set(CMAKE_CXX_STANDARD 11)

if(USE_MPI)
	add_definitions(-DUSE_MPI)
	execute_process(COMMAND sed "s/#define NOTHING/#define USE_MPI/g" ${CMAKE_CURRENT_SOURCE_DIR}/kittie.h OUTPUT_FILE ${CMAKE_CURRENT_BINARY_DIR}/kittie.h)
else()
	execute_process(COMMAND sed "s/#define NOTHING/#define NOTHING/g" ${CMAKE_CURRENT_SOURCE_DIR}/kittie.h OUTPUT_FILE ${CMAKE_CURRENT_BINARY_DIR}/kittie.h)
endif()

set(lib_objects ${CMAKE_CURRENT_SOURCE_DIR}/kittie.cpp)
add_library(kittie ${lib_objects})
set_property(TARGET kittie PROPERTY EXPORT_NAME cxx)

target_link_libraries(kittie PUBLIC adios2::adios2 PRIVATE yaml-cpp::yaml-cpp)
target_include_directories(kittie
	PUBLIC 
	$<BUILD_INTERFACE:${CMAKE_BINARY_DIR}/src/cpp>
	$<INSTALL_INTERFACE:${CMAKE_INSTALL_PREFIX}/include>
)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/kittie.h DESTINATION ${CMAKE_INSTALL_PREFIX}/include)

install(
	TARGETS kittie
	EXPORT effis-targets
	DESTINATION ${CMAKE_INSTALL_PREFIX}/lib
)

