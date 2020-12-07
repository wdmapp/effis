module kittie
	use kittie_internal

	implicit none


	type coupling_helper
		character(len=:), allocatable :: filename
		character(len=:), allocatable :: groupname
		type(adios2_engine) :: engine
		type(adios2_io) :: io
		integer :: mode
		logical :: WriteMode=.false.
		integer :: comm
		integer :: rank
		integer :: CurrentStep
		logical :: usesfile
		logical :: alive=.false.
		logical :: fileopened=.false.
		logical :: FindStep = .false.
		character(len=:), allocatable :: engine_type

		logical :: timed=.false., timeinit=.false.
		character(len=:), allocatable :: timingfile, timinggroup
		real(8), dimension(1) :: starttime, endtime, othertime, totaltime
		type(adios2_engine) :: timeengine
		type(adios2_io) :: timingio

	end type coupling_helper


	type(coupling_helper), pointer :: common_helper
	type(coupling_helper), dimension(:), allocatable, target :: helpers

	character(len=8), parameter :: writing=".writing"
	character(len=8), parameter :: reading=".reading"
	character(len=:), allocatable :: myreading, code_name !, app_name
	character(len=128), dimension(:), allocatable :: allreading
	logical, dimension(:), allocatable :: readexists

	! These need to be read from files at startup
	integer :: ngroupnames, ncodes, nnames, nGroupsSet
	character(len=512) :: timingdir
	character(len=128), dimension(:), allocatable :: groupnames, codenames, names, engines
	character(len=256), dimension(:), allocatable :: kittie_filenames
	character(len=128), dimension(:, :), allocatable :: params, values !, plots, 
	integer, dimension(:), allocatable ::  nparams!, nplots,


	integer :: ntimers=0
	character(len=128), dimension(:), allocatable :: timers
	type(adios2_io), dimension(:), allocatable :: timer_ios
	type(adios2_engine), dimension(:), allocatable :: timer_engines
	real(8), dimension(:), allocatable :: start_times, stop_times


	integer :: kittie_comm, kittie_rank, kittie_StepNumber
	real(8) :: kittie_StepPhysical
	logical :: kittie_StepInit=.false.
	logical :: kittie_AllStep=.false.
	type(adios2_io) :: kittie_StepIO
	type(adios2_engine) :: kittie_StepEngine
	logical, dimension(:), allocatable :: kittie_addstep, kittie_timed
	character(len=:), allocatable :: kittie_StepGroupname


	contains

		subroutine SetMaxGroups(num)
			integer, intent(in) :: num
			ngroupnames = num
			allocate(groupnames(ngroupnames), helpers(ngroupnames))
			nGroupsSet = 0
		end subroutine SetMaxGroups

		subroutine SetMaxTimers(num)
			integer, intent(in) :: num
			!ntimers = num
			allocate(timers(num), timer_ios(num), timer_engines(num), start_times(num), stop_times(num))
			start_times(:) = -1
			stop_times(:) = -1
		end subroutine SetMaxTimers


		subroutine kittie_read_codes_file(filename)
			character(len=*), intent(in) :: filename
			character(len=128) :: codename
			logical :: exists
			integer :: pid, i, j, k
			namelist /codes/ ncodes, codename
			namelist /codes_list/ codenames

			inquire(file=trim(filename), exist=exists)
			if (exists) then
				open(unit=iounit, file=trim(filename), action='read')
				read(iounit, nml=codes)
				close(iounit)
				allocate(codenames(ncodes))
				open(unit=iounit, file=trim(filename), action='read')
				read(iounit, nml=codes_list)
				close(iounit)

				myreading = string_copy(reading // '-' // trim(codename))
				allocate(allreading(ncodes))
				do i=1, ncodes
					allreading(i) = trim(reading) // '-' // trim(codenames(i))
				end do
			else
				codename = "unknown"
				myreading = string_copy(reading)
				ncodes = 1
				allocate(allreading(ncodes))
				allreading(1) = trim(reading)
			end if
			code_name = string_copy(codename)

		end subroutine kittie_read_codes_file


		subroutine kittie_get_helper(groupname, helper)
			character(len=*), intent(in) :: groupname
			type(coupling_helper), pointer, intent(out) :: helper
			integer :: i
			!do i=1, size(helpers)
			do i=1, nGroupsSet
				if (trim(groupname) == trim(groupnames(i))) then
					helper => helpers(i)
					exit
				end if
			end do
		end subroutine kittie_get_helper


		subroutine kittie_read_groups_file(filename)
			character(len=*), intent(in) :: filename
			logical :: exists
			integer :: maxsize, maxparams, i, ierr
			type(adios2_io) :: io
			namelist /ionames/ nnames, timingdir
			namelist /ionames_list/ names, engines, nparams, kittie_addstep, kittie_filenames, kittie_timed !, nplots
			namelist /params_list/ params, values
			!namelist /plots_list/ plots

			inquire(file=trim(filename), exist=exists)

			if (exists) then

				open(unit=iounit, file=trim(filename), action='read')
				read(iounit, nml=ionames)
				close(iounit)

				!allocate(names(nnames), engines(nnames), nplots(nnames), nparams(nnames))
				allocate(names(nnames), engines(nnames), nparams(nnames), kittie_addstep(nnames), &
					kittie_filenames(nnames), kittie_timed(nnames))
				do i=1, nnames
					engines(i) = ""
					nparams(i) = 0
					!nplots(i) = 0
					kittie_addstep(i) = .false.
					kittie_timed(i) = .false.
					kittie_filenames(i) = ""
				end do
				open(unit=iounit, file=trim(filename), action='read')
				read(iounit, nml=ionames_list)
				close(iounit)

				if (nnames > 0) then
					maxparams = maxval(nparams)
					allocate(params(nnames, maxparams), values(nnames, maxparams))
					open(unit=iounit, file=trim(filename), action='read')
					read(iounit, nml=params_list)
					close(iounit)
					!maxsize = maxval(nplots)
					!allocate(plots(nnames, maxsize))
					!open(unit=iounit, file=trim(filename), action='read')
					!read(iounit, nml=plots_list)
					!close(iounit)
				end if

			end if

		end subroutine kittie_read_groups_file


		subroutine wlock(wfile)
			character(len=*), intent(in) :: wfile
			logical :: exists
			inquire(file=trim(wfile), exist=exists)
			if (.not. exists) then
				call touch_file(wfile)
			end if
		end subroutine wlock

		subroutine nothing_writing(wfile)
			character(len=*), intent(in) :: wfile
			logical :: exists
			inquire(file=trim(wfile), exist=exists)
			do while(exists)
				inquire(file=trim(wfile), exist=exists)
			end do
		end subroutine nothing_writing

		subroutine nothing_reading(helper)
			type(coupling_helper), intent(in) :: helper
			integer :: i
			character(len=512) :: rfile
			logical :: readexists
			do i=1, ncodes
				rfile = trim(helper%filename) // trim(allreading(i))
				inquire(file=trim(rfile), exist=readexists)
				do while(readexists)
					inquire(file=trim(rfile), exist=readexists)
				end do
			end do
		end subroutine

		subroutine wait_data_existence(helper, suffix)
			type(coupling_helper), intent(in) :: helper
			character(len=*), intent(in), optional :: suffix
			logical :: exists
			if (present(suffix)) then
				inquire(file=trim(helper%filename//trim(suffix)), exist=exists)
				do while(.not.exists) 
					inquire(file=trim(helper%filename//trim(suffix)), exist=exists)
				end do
			else
				inquire(file=trim(helper%filename), exist=exists)
				do while(.not.exists) 
					inquire(file=trim(helper%filename), exist=exists)
				end do
			endif
		end subroutine wait_data_existence

		subroutine rlock(rfile)
			character(len=*), intent(in) :: rfile
			logical :: exists
			inquire(file=trim(rfile), exist=exists)
			if (.not. exists) then
				call touch_file(rfile)
			end if
		end subroutine rlock


		recursive subroutine until_nonexistent(helper, verify_level)
			type(coupling_helper), intent(in) :: helper
			integer, intent(in), optional :: verify_level
			logical :: rexists, wexists, redo, found
			integer :: v, vlevel, i
			character(len=512) :: rfile, wfile

			if (present(verify_level)) then
				vlevel = verify_level
			else
				vlevel = 3
			end if
			redo = .false.

			wfile = trim(helper%filename) // writing

			if (helper%WriteMode) then
				call wlock(wfile)
				call nothing_reading(helper)
			else
				rfile = trim(helper%filename) // myreading
				if ((trim(helper%engine_type) == "BP4") .and. (helper%mode == adios2_mode_read)) then
					call wait_data_existence(helper, suffix="/md.idx")
					call wait_data_existence(helper, suffix="/md.0")
				else
					call wait_data_existence(helper)
				endif
				call nothing_writing(wfile)
				call rlock(rfile)

				do v=1, vlevel
					inquire(file=trim(wfile), exist=wexists)
					if (wexists) then
						call delete_existing(rfile)
						redo = .true.
						exit
					end if
				end do

			end if

			if (redo) then
				call until_nonexistent(helper, verify_level=vlevel)
			end if

		end subroutine until_nonexistent


		subroutine lock_logic(helper, yes)
			type(coupling_helper), intent(in) :: helper
			logical, intent(in) :: yes

			if (yes) then
				call until_nonexistent(helper)
			else
				if (helper%WriteMode) then
					call delete_existing(helper%filename//writing)
				else if (helper%mode == adios2_mode_read) then
					call delete_existing(helper%filename//myreading)
				end if
			end if

		end subroutine lock_logic


		subroutine lock_state(helper, yes)
			type(coupling_helper), intent(in) :: helper
			logical, intent(in) :: yes
			integer :: ierr, rank, stat

			if (.not.yes) then
				call mpi_barrier(helper%comm, ierr)
			end if

			if (helper%rank == 0) then
				call lock_logic(helper, yes)
			end if

			if (yes) then
				call mpi_barrier(helper%comm, ierr)
			end if

		end subroutine lock_state

		subroutine kittie_close(helper, iierr, closed)
			type(coupling_helper), intent(inout) :: helper
			integer, intent(out), optional :: iierr
			logical, intent(in), optional :: closed
			logical :: doclose
			integer :: ierr

			if (.not. present(closed)) then
				doclose = .true.
			else if (closed) then
				doclose = .false.
			else
				doclose = .true.
			end if

			if (helper%fileopened) then

				if (helper%usesfile) then
					call lock_state(helper, .true.)
				end if

				if (doclose) then
					call adios2_close(helper%engine, ierr)
				end if
				helper%fileopened = .false.

				if (helper%usesfile) then
					call lock_state(helper, .false.)
				end if

			end if

			if (present(iierr)) then
				iierr = ierr
			end if

		end subroutine kittie_close


		subroutine AddStep(helper)
			type(coupling_helper), intent(inout) :: helper
			logical :: find
			integer :: i, ierr
			type(adios2_variable) :: varid
			find = .false.

			if (.not.helper%FindStep) then

				if (kittie_AllStep) then
					find = .true.
				else
					do i=1, nnames
						if (trim(helper%groupname) == trim(names(i)) .and. kittie_addstep(i)) then
							find = .true.
							exit
						end if
					end do
				end if

				if (find) then
					helper%FindStep = .true.
					if (helper%WriteMode .and. (helper%rank == 0)) then
						call adios2_define_variable(varid, helper%io, "_StepNumber",   adios2_type_integer4, ierr)
						call adios2_define_variable(varid, helper%io, "_StepPhysical", adios2_type_dp,       ierr)
					end if
				end if

			end if

			if (helper%FindStep .and. helper%WriteMode .and. (helper%rank == 0)) then
				call adios2_put(helper%engine, "_StepNumber", kittie_StepNumber, ierr)
				call adios2_put(helper%engine, "_StepPhysical", kittie_StepPhysical, ierr)
			end if

		end subroutine AddStep


		subroutine kittie_couple_end_step(helper, iierr)
			type(coupling_helper), intent(inout) :: helper
			integer, intent(out), optional :: iierr
			integer :: ierr

			call AddStep(helper)

			if (helper%timed .and. use_mpi) then
				helper%othertime(1) = mpi_wtime() - helper%othertime(1)
				helper%endtime(1) = mpi_wtime()
			end if

			if (helper%usesfile) then
				call lock_state(helper, .true.)
			end if

			call adios2_end_step(helper%engine, ierr)

			if (helper%usesfile) then
				call lock_state(helper, .false.)

				if ((helper%mode == adios2_mode_read) .and. helper%fileopened) then
					call adios2_close(helper%engine, ierr)
					call adios2_remove_all_variables(helper%io, ierr)
					call adios2_remove_all_attributes(helper%io, ierr)
					helper%fileopened = .false.
				end if
			end if

			if (helper%timed .and. use_mpi) then
				helper%totaltime(1) = mpi_wtime() - helper%totaltime(1)
				helper%endtime(1) = mpi_wtime() - helper%endtime(1)
				call adios2_begin_step(helper%timeengine, adios2_step_mode_append, ierr)
				call adios2_put(helper%timeengine, "start", helper%starttime, ierr)
				call adios2_put(helper%timeengine, "end",   helper%endtime,   ierr)
				call adios2_put(helper%timeengine, "other", helper%othertime, ierr)
				call adios2_put(helper%timeengine, "total", helper%totaltime, ierr)
				call adios2_end_step(helper%timeengine, ierr)
			end if

			if (present(iierr)) then
				iierr = ierr
			end if

		end subroutine kittie_couple_end_step


		function which_engine(io) result(ret)
			type(adios2_io), intent(in) :: io
			integer :: ierr
			character(:), allocatable :: res, ret
			res = capitalize(io%engine_type)
			if ((trim(res) == 'BPFILE') .or. (trim(res) == 'BP') .or. (trim(res) == 'BP1') .or. (trim(res) == 'BP2') .or. (trim(res) == 'BP3')) then
#				ifdef ADIOS2_OLD_STEP
					ret = string_copy("BP3")
#				else
					ret = string_copy("BP4")
#				endif
			else
				ret = string_copy(res)
			end if
			deallocate(res)
		end function which_engine


		function uses_files(engine_type) result(res)
			character(len=*), intent(in) :: engine_type
			integer :: ierr
			logical :: res

			if ((trim(engine_type) == 'HDF5') .or. (trim(engine_type) == 'BP3')) then
				res = .true.
			else
				res = .false.
			end if
		end function uses_files


		function file_seek(helper, step, timeout, iostatus) result(found)
			type(coupling_helper), intent(inout) :: helper
			integer, intent(in) :: step
			real(4), intent(in) :: timeout
			integer, intent(out) :: iostatus

			integer :: ierr, i
			integer(kind=8) :: current_step, cs
			logical :: found, exists

			found = .false.
			current_step = -1
			call lock_state(helper, .true.)

			if (.not.helper%fileopened) then
#				ifdef USE_MPI
					call adios2_open(helper%engine, helper%io, helper%filename, helper%mode, helper%comm, ierr)
#				else
					call adios2_open(helper%engine, helper%io, helper%filename, helper%mode, ierr)
#				endif
				helper%fileopened = .true.
			endif


			do while (.true.)
#				ifdef ADIOS2_OLD_STEP
					call adios2_begin_step(helper%engine, adios2_step_mode_next_available, timeout, iostatus, ierr)
#				else
					call adios2_begin_step(helper%engine, adios2_step_mode_read, timeout, iostatus, ierr)
#				endif

				if (iostatus == 0) then
					current_step = current_step + 1
				else
					exit
				end if

				if (current_step == step) then
					found = .true.
					helper%CurrentStep = helper%CurrentStep + 1
					exit
				end if

				call adios2_end_step(helper%engine, ierr)
			end do

			call lock_state(helper, .false.)
			if (.not.found) then
				call adios2_close(helper%engine, ierr)
				helper%fileopened = .false.
				call adios2_remove_all_variables(helper%io, ierr)
				call adios2_remove_all_attributes(helper%io, ierr)

				inquire(file=trim(helper%filename)//".done", exist=exists)
				if (.not.exists) then
					iostatus = adios2_step_status_not_ready
				end if

			end if

		end function file_seek


		subroutine kittie_couple_open(helper)
			type(coupling_helper), intent(inout) :: helper
			integer :: ierr, rank
			
			if (helper%usesfile) then
				call lock_state(helper, .true.)
			end if

#			ifdef USE_MPI
				if ((trim(helper%engine_type) == "BP4") .and. (helper%mode == adios2_mode_read)) then
					call wait_data_existence(helper, suffix="/md.idx")
					call wait_data_existence(helper, suffix="/md.0")
				end if
				call adios2_open(helper%engine, helper%io, helper%filename, helper%mode, helper%comm, ierr)
#			else
				call adios2_open(helper%engine, helper%io, helper%filename, helper%mode, ierr)
#			endif


			if (helper%usesfile) then
				call lock_state(helper, .false.)
			end if

			helper%fileopened = .true.
		end subroutine kittie_couple_open


		subroutine kittie_finalize(iierr, closed)
			integer, intent(out), optional :: iierr
			character(len=*), dimension(:), intent(in), optional :: closed
			integer :: i, j, rank, ierr
			logical :: wasclosed

			wasclosed = .false.
			do i=1, size(helpers)
				if (.not.present(closed)) then
					call kittie_close(helpers(i), ierr)
				else

					do j=1, size(closed)
						if (trim(helpers(i)%filename) == trim(closed(j))) then
							call kittie_close(helpers(i), ierr, closed=.true.)
							wasclosed = .true.
							exit
						end if
					end do

					if (.not.wasclosed) then
						call kittie_close(helpers(i), ierr)
					end if

				end if

				if ((helpers(i)%rank == 0) .and. helpers(i)%WriteMode) then
					call touch_file(trim(helpers(i)%filename)//'.done')
				end if
			end do

			if (kittie_StepInit) then
				open(unit=iounit, file=trim(kittie_StepGroupname)//".done", status='new')
				write(iounit, "(I0)") kittie_StepNumber
				close(iounit)
				call adios2_close(kittie_StepEngine, ierr)
			end if

			call adios2_finalize(kittie_adios, ierr)

			if (present(iierr)) then
				iierr = ierr
			end if

		end subroutine kittie_finalize


#		ifdef USE_MPI

			subroutine kittie_initialize(comm, xml, ngroups, numtimers, ierr)
				! Intialize Kittie's ADIOS-2 namespace
				integer, intent(in)  :: comm
				character(len=*), intent(in), optional :: xml
				integer, intent(in), optional :: ngroups, numtimers
				integer, intent(out), optional :: ierr
				integer :: iierr
				character(len=10) :: num

				if (present(ngroups)) then
					call SetMaxGroups(ngroups)
				else
					call SetMaxGroups(25)
				end if

				if (present(numtimers)) then
					call SetMaxTimers(numtimers)
				else
					call SetMaxTimers(25)
				end if

				call mpi_comm_dup(comm, kittie_comm, iierr)
				call mpi_comm_rank(comm, kittie_rank, iierr)

				if (present(xml)) then
					call adios2_init(kittie_adios, trim(xml), kittie_comm, adios2_debug_mode_on, iierr)
				else
					call adios2_init(kittie_adios, kittie_comm, adios2_debug_mode_on, iierr)
				end if

				call get_environment_variable("KITTIE_NUM", num)
				call kittie_read_codes_file(".kittie-codenames-" // trim(num) // ".nml")
				call kittie_read_groups_file(  ".kittie-groups-" // trim(num) // ".nml")
				kittie_StepGroupname = string_copy(trim(code_name) // "-step")

				if (present(ierr)) then
					ierr = iierr
				end if
			end subroutine kittie_initialize

#		else

			subroutine kittie_initialize(xml, ngroups, numtimers, ierr)
				! Intialize Kittie's ADIOS-2 namespace
				character(len=*), intent(in), optional :: xml
				integer, intent(in), optional :: ngroups, numtimers
				integer, intent(out), optional :: ierr
				integer :: iierr
				character(len=10) :: num

				if (present(ngroups)) then
					call SetMaxGroups(ngroups)
				else
					call SetMaxGroups(25)
				end if

				if (present(numtimers)) then
					call SetMaxTimers(numtimers)
				else
					call SetMaxTimers(25)
				end if

				kittie_rank = 0

				if (present(xml)) then
					call adios2_init(kittie_adios, trim(xml), adios2_debug_mode_on, iierr)
				else
					call adios2_init(kittie_adios, adios2_debug_mode_on, iierr)
				end if

				call get_environment_variable("KITTIE_NUM", num)
				call kittie_read_codes_file(".kittie-codenames-" // trim(num) // ".nml")
				call kittie_read_groups_file(  ".kittie-groups-" // trim(num) // ".nml")
				kittie_StepGroupname = string_copy(trim(code_name) // "-step")

				if (present(ierr)) then
					ierr = iierr
				end if

			end subroutine kittie_initialize

#		endif


		function KittieDeclareIO(groupname, iierr) result(io)
			! Initialize a new Kittie coupling I/O group
			character(len=*), intent(in) :: groupname
			integer, intent(out), optional :: iierr
			integer :: i, j, ierr
			type(adios2_io) :: io

			nGroupsSet = nGroupsSet + 1
			groupnames(nGroupsSet) = trim(groupname)

			call adios2_declare_io(io, kittie_adios, trim(groupname), ierr)

			do i=1, nnames
				if ((trim(names(i)) == trim(groupname)) .and. (trim(engines(i)) /= "")) then
					call adios2_set_engine(io, trim(engines(i)), ierr)
					do j=1, nparams(i)
						call adios2_set_parameter(io, trim(params(i, j)), trim(values(i, j)), ierr)
					end do
				end if
			end do

			if (present(iierr)) then
				iierr = ierr
			end if
		end function KittieDeclareIO


		subroutine kittie_open(helper, groupname, filename, mode, comm, ierr)
			type(coupling_helper), intent(inout) :: helper
			character(len=*), intent(in) :: groupname
			character(len=*), intent(in) :: filename
			integer, intent(in) :: mode
			integer, intent(in),  optional :: comm
			integer, intent(in),  optional :: ierr

			type(adios2_io) :: io, timingio
			type(adios2_engine) :: engine
			type(adios2_variable) :: varid
			integer :: iierr, comm_size, i
			integer(8), dimension(1) :: gdims, offs, locs

			call adios2_at_io(io, kittie_adios, trim(groupname), iierr)

			if (present(comm) .and. .not.helper%alive) then
				call mpi_comm_dup(comm, helper%comm, iierr)
			else if (use_mpi .and. .not.helper%alive) then
				call mpi_comm_dup(kittie_comm, helper%comm, iierr)
			endif 

			if (.not.helper%alive) then
				call mpi_comm_rank(helper%comm, helper%rank, iierr)
				helper%engine_type = which_engine(io)
				helper%usesfile = uses_files(helper%engine_type)
				helper%mode = mode
				if ((helper%mode == adios2_mode_write) .or. (helper%mode == adios2_mode_append)) then
					helper%WriteMode = .true.
				end if
				helper%CurrentStep = -1
			end if


			if (.not.helper%fileopened) then
				helper%io = io
				helper%groupname = string_copy(trim(groupname))

				helper%filename = string_copy(trim(filename))
				do i=1, nnames

					if (trim(helper%groupname) == trim(names(i))) then
						if (kittie_filenames(i) /= "") then
							helper%filename = string_copy(trim(kittie_filenames(i)))
						else
							helper%filename = string_copy(trim(filename))
						end if

						if (kittie_timed(i) .and. use_mpi .and. .not. helper%fileopened) then
							helper%timed = .true.
							helper%timingfile = string_copy(trim(timingdir)//"/"//trim(code_name)//trim(groupname)//".bp")
							helper%timinggroup = string_copy(trim(groupname)//"-timing")

							if (.not.helper%timeinit) then
								call mpi_comm_size(helper%comm, comm_size, iierr)
								gdims(1) = comm_size
								offs(1)  = helper%rank
								locs(1)  = 1

								call adios2_declare_io(helper%timingio, kittie_adios, trim(helper%timinggroup), iierr)
								call adios2_define_variable(varid, helper%timingio, "start", adios2_type_dp, 1, gdims, offs, locs, .true., iierr)
								call adios2_define_variable(varid, helper%timingio, "end",   adios2_type_dp, 1, gdims, offs, locs, .true., iierr)
								call adios2_define_variable(varid, helper%timingio, "other", adios2_type_dp, 1, gdims, offs, locs, .true., iierr)
								call adios2_define_variable(varid, helper%timingio, "total", adios2_type_dp, 1, gdims, offs, locs, .true., iierr)

								call adios2_at_io(helper%timingio, kittie_adios, trim(helper%timinggroup), iierr)
#								ifdef ADIOS2_OLD_STEP
									call adios2_set_engine(helper%timingio, "BP3", iierr)
#								else
									call adios2_set_engine(helper%timingio, "BP4", iierr)
#								endif

#								ifdef USE_MPI
									call adios2_open(helper%timeengine, helper%timingio, helper%timingfile, adios2_mode_write, helper%comm, iierr)
#								else
									call adios2_open(helper%timeengine, helper%timingio, helper%timingfile, adios2_mode_write, iierr)
#								endif

								helper%timeinit = .true.
							end if
						else
							helper%timed = .false.
						end if

					end if
				end do
			end if


			if (.not.helper%fileopened) then
				call kittie_couple_open(helper)
			end if

		end subroutine kittie_open


		subroutine kittie_couple_start(helper, step, timeout, iostatus, ierr)
			type(coupling_helper), intent(inout) :: helper
			integer, intent(in),  optional :: step
			real(4), intent(in),  optional :: timeout
			integer, intent(out), optional :: iostatus
			integer, intent(out), optional :: ierr

			type(adios2_io) :: io, timingio
			type(adios2_engine) :: engine
			integer :: iierr, istep
			integer(8), dimension(1) :: gdims, offs, locs
			logical :: found

			real(4) :: ftimeout
			integer :: fstatus

			if (present(timeout)) then
				ftimeout = timeout
			else
				ftimeout = -1.0
			end if


			if (present(step)) then
				istep = step
			end if

			if (helper%timed .and. use_mpi) then
				helper%starttime(1) = mpi_wtime()
				helper%totaltime(1) = mpi_wtime()
			end if


			if (helper%WriteMode) then
				if (.not.helper%fileopened) then
					call kittie_couple_open(helper)
				end if
				call adios2_begin_step(helper%engine, adios2_step_mode_append, iierr)

			else if (helper%mode == adios2_mode_read) then

				if (helper%usesfile) then
					if (.not.present(step)) then
						istep = helper%CurrentStep + 1
					end if

					found = .false.
					do while (.not.found)
						found = file_seek(helper, istep, ftimeout, fstatus)
						if (ftimeout > -1.0) then
							exit
						end if
					end do

				else
					if (.not.helper%fileopened) then
						call kittie_couple_open(helper)
					end if

#					ifdef ADIOS2_OLD_STEP
						call adios2_begin_step(helper%engine, adios2_step_mode_next_available, ftimeout, fstatus, iierr)
#					else
						call adios2_begin_step(helper%engine, adios2_step_mode_read, ftimeout, fstatus, iierr)
#					endif

				end if

			end if

			helper%alive = .true.

			if (present(ierr)) then
				ierr = iierr
			end if

			if (present(iostatus)) then
				iostatus = fstatus
			end if

			if (helper%timed .and. use_mpi) then
				helper%starttime(1) = mpi_wtime() - helper%starttime(1)
				helper%othertime(1) = mpi_wtime()
			end if

		end subroutine kittie_couple_start


		subroutine write_step(physical, num)
			real(8), intent(in) :: physical
			integer(4), intent(in) :: num
			integer :: ierr
			type(adios2_variable) :: varid


			if (kittie_rank == 0) then

				kittie_StepPhysical = physical
				kittie_StepNumber = num

				if (.not. kittie_StepInit) then
					!!call adios2_declare_io(kittie_StepIO, kittie_adios, trim(kittie_StepGroupname), ierr)
					kittie_StepIO = KittieDeclareIO(trim(kittie_StepGroupname), ierr)
					call adios2_define_variable(varid, kittie_StepIO, "StepNumber",   adios2_type_integer4, ierr)
					call adios2_define_variable(varid, kittie_StepIO, "StepPhysical", adios2_type_dp,       ierr)

					!call adios2_set_engine(kittie_StepIO, "SST", ierr)
					!call adios2_set_parameter(kittie_StepIO, "RendezvousReaderCount", "0", ierr)
					!call adios2_set_parameter(kittie_StepIO, "QueueLimit", "1", ierr)
					!call adios2_set_parameter(kittie_StepIO, "QueueFullPolicy", "Discard", ierr)

#					ifdef USE_MPI
						call adios2_open(kittie_StepEngine, kittie_StepIO, trim(kittie_StepGroupname)//".bp", adios2_mode_write, mpi_comm_self, ierr)
#					else
						call adios2_open(kittie_StepEngine, kittie_StepIO, trim(kittie_StepGroupname)//".bp", adios2_mode_write, ierr)
#					endif

					kittie_StepInit = .true.
				end if

				call adios2_begin_step(kittie_StepEngine, adios2_step_mode_append, ierr)
				call adios2_put(kittie_StepEngine, "StepNumber", kittie_StepNumber, ierr)
				call adios2_put(kittie_StepEngine, "StepPhysical", kittie_StepPhysical, ierr)
				call adios2_end_step(kittie_StepEngine, ierr)

			end if
		end subroutine write_step


		subroutine start_timer(tname, comm)
			character(len=*), intent(in) :: tname
			integer, intent(in), optional :: comm
			integer :: i, ierr, rank, procs
			logical :: found
			character(len=256) :: timefile
			type(adios2_variable) :: varid
			integer(8), dimension(1) :: tdims, toffs, tlocs

#			ifndef USE_MPI
				write(0, "('Need MPI to use EFFIS timers from Fortan')")

#			else
				found = .false.

				do i=1, ntimers
					if (trim(timers(i)) == trim(tname)) then
						found = .true.
						exit
					end if
				end do
				
				if (.not.found) then
					ntimers = ntimers + 1
					timers(ntimers) = trim(tname)
					i = ntimers

					timefile = trim(timingdir) // '/' // trim(tname) // '.bp'
					call adios2_declare_io(timer_ios(i), kittie_adios, trim(timers(i)), ierr)

					if (present(comm)) then
						call mpi_comm_rank(comm, rank, ierr)
						call mpi_comm_size(comm, procs, ierr)
						tdims(1) = procs
						toffs(1) = rank
						tlocs(1) = 1
						call adios2_define_variable(varid, timer_ios(i), "time", adios2_type_dp, 1, tdims, toffs, tlocs, .true., ierr)
						call adios2_open(timer_engines(i), timer_ios(i), trim(timefile), adios2_mode_write, comm, ierr)
					else
						call mpi_comm_rank(kittie_comm, rank, ierr)
						call mpi_comm_size(kittie_comm, procs, ierr)
						tdims(1) = procs
						toffs(1) = rank
						tlocs(1) = 1
						call adios2_define_variable(varid, timer_ios(i), "time", adios2_type_dp, 1, tdims, toffs, tlocs, .true., ierr)
						call adios2_open(timer_engines(i), timer_ios(i), trim(timefile), adios2_mode_write, kittie_comm, ierr)
					end if
				end if

				start_times(i) = mpi_wtime()
#			endif

		end subroutine start_timer


		subroutine stop_timer(tname)
			character(len=*), intent(in) :: tname
			integer :: i, ierr
			logical :: found

#			ifndef USE_MPI
				write(0, "('Need MPI to use EFFIS timers from Fortan')")

#			else
				found = .false.
				do i=1, ntimers
					if (trim(timers(i)) == trim(tname)) then
						found = .true.
						exit
					end if
				end do
				
				if (.not.found .or. (start_times(i) <= stop_times(i))) then
					write(0, "('Found stop without matching start for timer ', A)") trim(tname)
				else
					stop_times(i) = mpi_wtime()
					call adios2_begin_step(timer_engines(i), adios2_step_mode_append, ierr)
					call adios2_put(timer_engines(i), "time", (/stop_times(i) - start_times(i)/), ierr)
					call adios2_end_step(timer_engines(i), ierr)
					start_times(i) = stop_times(i)
				end if
#			endif

		end subroutine stop_timer


end module kittie

