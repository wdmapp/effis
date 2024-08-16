preprocess()
add_definitions(${fotran_free_flag})

add_executable(writer ${CMAKE_CURRENT_BINARY_DIR}/writer-effis.F90)
target_link_libraries(writer kittie_f adios2::adios2_f)

add_executable(reader ${CMAKE_CURRENT_BINARY_DIR}/reader-effis.F90)
target_link_libraries(reader kittie_f adios2::adios2_f)

install(TARGETS writer DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Fortran)
install(TARGETS reader DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Fortran)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/example.yaml DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Fortran)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/setup.sh DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Fortran)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/writer.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Fortran)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/reader.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Fortran)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/writer-effis.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Fortran)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/reader-effis.F90 DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Fortran)
