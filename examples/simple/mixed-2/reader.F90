program reader
	use adios2
	use mpi
	implicit none

	integer :: comm, ierr, rank, nproc, i, read_status
	integer(8) :: current_step
	type(adios2_adios) :: adios
	type(adios2_io) :: io
	type(adios2_engine) :: engine
	type(adios2_variable) :: varid

	call mpi_init(ierr)
	call mpi_comm_dup(MPI_COMM_WORLD, comm, ierr)


    !@effis-init comm=comm
	call adios2_init(adios, comm, ierr)

    !@effis-begin "Jabberwocky"->"Jabberwocky"
    call adios2_declare_io(io, adios, "Jabberwocky", ierr)
	call adios2_open(engine, io, "Jabberwocky.bp", adios2_mode_read, comm, ierr)

	do while (.true.)

        call adios2_begin_step(engine, adios2_step_mode_read, 1.0, read_status, ierr)

        if (read_status == adios2_step_status_not_ready) then
            cycle
		else if (read_status /= adios2_step_status_ok) then
            exit
		end if

		call adios2_current_step(current_step, engine, ierr)
        write (6, "('APP step: ', i0)") current_step
		call adios2_end_step(engine, ierr)

	end do

	call adios2_close(engine, ierr)
    !@effis-end

    !@effis-finalize

end program reader
