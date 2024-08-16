preprocess()
set(CMAKE_CXX_STANDARD 11)

add_executable(writer-complex ${CMAKE_CURRENT_BINARY_DIR}/writer-effis.cpp)
target_link_libraries(writer-complex kittie adios2::adios2)
set_target_properties(writer-complex PROPERTIES OUTPUT_NAME writer)

add_executable(reader-complex ${CMAKE_CURRENT_BINARY_DIR}/reader-effis.F90)
target_link_libraries(reader-complex kittie_f adios2::adios2_f)
set_target_properties(reader-complex PROPERTIES OUTPUT_NAME reader)

install(TARGETS writer-complex DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/complex)
install(TARGETS reader-complex DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/complex)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/example.yaml DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/complex)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/writer.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/complex)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/reader.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/complex)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/writer-effis.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/complex)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/reader-effis.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/complex)
