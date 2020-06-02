execute_process(COMMAND ${PROJECT_SOURCE_DIR}/util/effis-cpp.py repo ${CMAKE_CURRENT_SOURCE_DIR} --tree-output=${CMAKE_CURRENT_BINARY_DIR})
set(CMAKE_CXX_STANDARD 11)

add_executable(writer-mixed-2 ${CMAKE_CURRENT_BINARY_DIR}/writer-effis.cpp)
target_link_libraries(writer-mixed-2 kittie adios2::adios2)
set_target_properties(writer-mixed-2 PROPERTIES OUTPUT_NAME writer)

add_executable(reader-mixed-2 ${CMAKE_CURRENT_BINARY_DIR}/reader-effis.F90)
target_link_libraries(reader-mixed-2 kittie_f adios2::adios2_f)
set_target_properties(reader-mixed-2 PROPERTIES OUTPUT_NAME reader)

install(TARGETS writer-mixed-2 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed-2)
install(TARGETS reader-mixed-2 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed-2)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/example.yaml DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed-2)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/writer.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed-2)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/reader.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed-2)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/writer-effis.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed-2)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/reader-effis.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/mixed-2)
