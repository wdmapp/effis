#ifndef __KITTIE_H__
#	define __KITTIE_H__

#define NOTHING

#	include <stdlib.h>
#	include <string>
#	include <vector>
#	include <algorithm>
#	include <iostream>
#	include <fstream>
#	include <cstdio>
#	include <unistd.h>
#	include <sys/stat.h>
#	include <adios2.h>


#	ifdef USE_MPI
#		include <mpi.h>
#	else
		class MPI_Comm {};
		int MPI_Comm_dup(MPI_Comm incomm, MPI_Comm* outcomm);
		int MPI_Comm_rank(MPI_Comm incomm, int* rank);
		int MPI_Barrier(MPI_Comm incomm);
#	endif


	namespace kittie 
	{

		class Coupler
		{
			public:
				std::string groupname;
				std::string filename;
				std::string cwriting;
				std::string creading;
				std::vector<std::string> allcreading;
				adios2::IO* io;
				adios2::Engine engine;
				adios2::Mode mode;
				bool WriteMode;
				MPI_Comm comm;
				int rank;
				int CurrentStep;
				int SimStep;
				bool init;
				bool opened;
				bool LockFile;
				bool FindStep;


				// Constructors
				Coupler(const std::string ingroupname);


				// Destructor
				//~Coupler();


				// Methods
				adios2::StepStatus begin_step(const int step, const double timeout=-1.0);
				adios2::StepStatus begin_step(const double timeout=-1.0);
				void end_step();
				void close();
				void finalize();
				void _open(MPI_Comm incomm, const std::string infilename, const adios2::Mode inmode);


			protected:
				void Until_Nonexistent_Write();
				void Until_Nonexistent_Read(int verify_level=3);
				void AcquireLock();
				void ReleaseLock();
				void _CoupleOpen();
				void _lockfile();
				void WaitDataExistence();
				void begin_write();
				adios2::StepStatus FileSeek(bool &found, const int step, const double timeout=-1.0);

				// @effis-timestep
				void AddStep();
		};


		class Timer
		{
			public:
				adios2::IO io;
				adios2::Engine engine;
				double start;
				double stop;
				Timer();
		};
	
		extern std::string timingdir;	
		extern std::map<std::string, Timer*> Timers;
		void stop_timer(std::string name);
		void start_timer(std::string name);
#		ifdef USE_MPI
			void start_timer(std::string name, MPI_Comm comm);
#		endif


		// MPI
		extern bool mpi;
		extern MPI_Comm comm;
		extern int rank;

		// ADIOS-related
		extern int ngroups;
		extern int nnames;
		extern adios2::ADIOS* adios;
		extern std::string myreading;
		extern std::string Codename;
		extern std::string writing;
		extern std::string reading;
		extern std::vector<std::string> _FileMethods;
		extern std::vector<std::string> _MetaMethods;
		extern std::vector<std::string> allreading;
		extern std::vector<std::string> groupnames;
		extern std::map<std::string, Coupler*> Couplers;
		extern std::map<std::string, std::string> filenames;
		extern std::map<std::string, std::string> setengines;
		extern std::map<std::string, std::map<std::string, std::string>> setparams;

		// @effis-timestep
		extern bool stepinit;
		extern bool AllStep;
		extern int _StepNumber;
		extern double _StepPhysical;
		extern adios2::Engine StepEngine;
		extern std::string StepGroupname;
		extern std::vector<std::string> StepGroups;


		void write_step(double physical, int number);
		void write_step(double physical, int number, MPI_Comm comm);

		void _buildyaml();
		void _groupsyaml();
		void _codesyaml();
		void _yaml_setup();

		bool Exists(std::string filename);
		void Touch(std::string filename);
		adios2::Engine _mopen(const std::string groupname, const std::string filename, const adios2::Mode mode, MPI_Comm comm);


		// "Public"
		void PlotMap(std::string plotname, std::string groupname, std::string directory);
		adios2::IO declare_io(const std::string groupname);
		void finalize();
		adios2::Engine open(const std::string groupname, const std::string filename, const adios2::Mode mode);

#	ifdef USE_MPI
			adios2::Engine open(const std::string groupname, const std::string filename, const adios2::Mode mode, MPI_Comm comm);
			void initialize(const std::string &filename="", MPI_Comm comm=MPI_COMM_SELF);
			void initialize(MPI_Comm comm);
#	else
			void initialize(const std::string &filename="");
			void initialize();
#	endif
		
	}

#endif
