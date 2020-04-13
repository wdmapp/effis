program writer
	use adios2
	use mpi
	implicit none

	integer, parameter :: nelems = 10
	integer(8), dimension(nelems) :: KnownInts
	real(8), dimension(nelems) :: RandomReals
	integer(8), dimension(2) :: GlobalDims, Offsets, LocalDims

	integer :: comm, ierr, rank, nproc, i
	real(8) :: dt=0.1
	type(adios2_adios) :: adios
	type(adios2_io) :: io
	type(adios2_engine) :: engine
	type(adios2_variable) :: varid

	call mpi_init(ierr)
	call mpi_comm_rank(MPI_COMM_WORLD, rank, ierr)

	call mpi_comm_split(MPI_COMM_WORLD, 0, rank, comm, ierr)
	call mpi_comm_rank(comm, rank, ierr)
	call mpi_comm_size(comm, nproc, ierr)


	do i=1, nelems
		KnownInts(i) = i
	end do

    !@effis-init comm=comm
	!call adios2_init(adios, comm, .true., ierr)

    !@effis-begin "Jabberwocky"->"Jabberwocky"
	call adios2_declare_io(io, adios, "Jabberwocky", ierr)

    GlobalDims(1) = nelems
    GlobalDims(2) = nproc
	Offsets(1) = 0
	Offsets(2) = rank
	LocalDims(1) = nelems
	LocalDims(2) = 1
    call adios2_define_variable(varid, io, "KnownInts",   adios2_type_integer8, 2, GlobalDims, Offsets, LocalDims, .true., ierr)
    call adios2_define_variable(varid, io, "RandomReals", adios2_type_dp,       2, GlobalDims, Offsets, LocalDims, .true., ierr)
	call adios2_open(engine, io, "Jabberwocky.bp", adios2_mode_write, comm, ierr)

	do i=1, 20
		call random_number(RandomReals)
		RandomReals = RandomReals + (rank + 1)
		dt = i * 1.0
        !@effis-timestep physical=dt, number=i
		call adios2_begin_step(engine, ierr)
		call adios2_put(engine, "KnownInts",   KnownInts, ierr)
		call adios2_put(engine, "RandomReals", RandomReals, ierr)
		call adios2_end_step(engine, ierr)
        write (*, "('Write step: ', i0)") i
		call sleep(1)
	end do

	call adios2_close(engine, ierr)
    !@effis-end

    !@effis-finalize
	call mpi_finalize(ierr)

end program writer
