add_subdirectory(Fortran)
add_subdirectory(Python)
add_subdirectory(cpp)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/matplotlibrc DESTINATION ${CMAKE_INSTALL_PREFIX}/plot PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ)
