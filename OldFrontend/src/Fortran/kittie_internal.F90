module kittie_internal

#	ifdef USE_MPI
		use mpi
#	endif

	use adios2

	implicit none


#	ifdef USE_MPI
		logical :: use_mpi=.true.
#	else
		logical :: use_mpi=.false.
#	endif

	logical :: touch = .false.
	integer :: iounit=2018

	! This is the namespace all the Kittie ADIOS-2 I/O lives in. Nicely, this will be completely independent of anything else ADIOS-2.
	type(adios2_adios) :: kittie_adios


	contains

		function string_copy(thing) result(new)
			character(len=*), intent(in) :: thing
			character(len=:), allocatable :: new
			allocate(character(len_trim(thing)) :: new)
			new = thing
		end function string_copy


		function capitalize(strIn) result(strOut)
			character(len=*), intent(in) :: strIn
			character(len=:), allocatable :: strOut
			integer :: i,j

			strOut = string_copy(strIn)
			do i = 1, len(strOut)
				j = iachar(strIn(i:i))
				if (j>= iachar("a") .and. j<=iachar("z") ) then
					strOut(i:i) = achar(iachar(strIn(i:i))-32)
				else
					strOut(i:i) = strIn(i:i)
				end if
			end do
		end function capitalize


		subroutine delete_existing(fname)
			character(len=*), intent(in) :: fname
			integer :: stat
			open(unit=iounit, iostat=stat, file=fname, status='old')
			close(iounit, status="delete")
		end subroutine delete_existing


		subroutine touch_file(fname)
			character(len=*), intent(in) :: fname
			!if (touch) then
			!	call execute_command_line("touch " // trim(fname))
			!else
				open(unit=iounit, file=trim(fname), status='new')
				close(iounit)
			!end if
		end subroutine touch_file


#		ifndef USE_MPI
			function mpi_wtime() result(time)
				real(8) :: time
				time = -1.0
			end function mpi_wtime

			subroutine mpi_barrier(comm, ierr)
				integer, intent(in) :: comm
				integer, intent(out) :: ierr
				ierr = 0
			end subroutine mpi_barrier

			subroutine mpi_comm_rank(comm, rank, ierr)
				integer, intent(in) :: comm
				integer, intent(out) :: rank, ierr
				rank = 0
				ierr = 0
			end subroutine mpi_comm_rank

			subroutine mpi_comm_size(comm, ssize, ierr)
				integer, intent(in) :: comm
				integer, intent(out) :: ssize, ierr
				ssize = 1
				ierr = 0
			end subroutine mpi_comm_size

			subroutine mpi_comm_dup(oldcom, newcomm, ierr)
				integer, intent(in) :: oldcom
				integer, intent(out) :: newcomm
				integer, intent(out) :: ierr
				newcomm = -1
				ierr = 0
			end subroutine mpi_comm_dup
#		endif


end module kittie_internal
