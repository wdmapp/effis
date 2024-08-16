preprocess()
set(CMAKE_CXX_STANDARD 11)

add_executable(writer-cpp ${CMAKE_CURRENT_BINARY_DIR}/writer-effis.cpp)
target_link_libraries(writer-cpp kittie adios2::adios2)
set_target_properties(writer-cpp PROPERTIES OUTPUT_NAME writer)

add_executable(reader-cpp ${CMAKE_CURRENT_BINARY_DIR}/reader-effis.cpp)
target_link_libraries(reader-cpp kittie adios2::adios2)
set_target_properties(reader-cpp PROPERTIES OUTPUT_NAME reader)

install(TARGETS writer-cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Cpp)
install(TARGETS reader-cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Cpp)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/example.yaml DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Cpp)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/writer.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Cpp)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/reader.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Cpp)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/writer-effis.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Cpp)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/reader-effis.cpp DESTINATION ${CMAKE_INSTALL_PREFIX}/examples/simple/Cpp)
