execute_process(COMMAND ${PROJECT_SOURCE_DIR}/util/effis-cpp.py repo ${CMAKE_CURRENT_SOURCE_DIR} --tree-output=${CMAKE_CURRENT_BINARY_DIR})
set(CMAKE_CXX_STANDARD 11)

add_executable(writer-mixed ${CMAKE_CURRENT_BINARY_DIR}/writer-kittie.F90)
target_compile_options(writer-mixed PUBLIC ${fotran_free_flag})
target_link_libraries(writer-mixed kittie_f adios2::adios2_f)
set_target_properties(writer-mixed PROPERTIES OUTPUT_NAME writer)

add_executable(reader-mixed ${CMAKE_CURRENT_BINARY_DIR}/reader-kittie.cpp)
target_link_libraries(reader-mixed kittie adios2::adios2)
set_target_properties(reader-mixed PROPERTIES OUTPUT_NAME reader)

install(
	TARGETS writer-mixed
	DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed
	PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
install(
	TARGETS reader-mixed
	DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed
	PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/example.yaml DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/writer.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/reader.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/writer-kittie.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/reader-kittie.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed)
