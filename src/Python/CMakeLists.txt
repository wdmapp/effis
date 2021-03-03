file(GLOB SRC ${CMAKE_CURRENT_SOURCE_DIR}/*)
foreach(SRCPATH ${SRC})
	file(COPY ${SRCPATH} DESTINATION ${CMAKE_CURRENT_BINARY_DIR} FOLLOW_SYMLINK_CHAIN)
endforeach(SRCPATH)

if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
	set(PYEXEC ${PYTHON_EXECUTABLE})
else()
	set(PYEXEC ${Python_EXECUTABLE})
endif()

install(CODE "execute_process(COMMAND ${PYEXEC} -s setup.py --no-user-cfg build WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})")
install(CODE "execute_process(COMMAND ${PYEXEC} -s setup.py --no-user-cfg install --prefix=${CMAKE_INSTALL_PREFIX} --single-version-externally-managed --root=/ WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})")
