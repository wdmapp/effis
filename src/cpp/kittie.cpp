#include "kittie.h"
#include "yaml-cpp/yaml.h"


#ifndef USE_MPI
	int MPI_Comm_dup(MPI_Comm incomm, MPI_Comm* outcomm)
	{
		return 0;
	}


	int MPI_Comm_rank(MPI_Comm incomm, int* rank)
	{
		*rank = 0;
		return 0;
	}


	int MPI_Barrier(MPI_Comm incomm)
	{
		return 0;
	}
#endif


// MPI
bool kittie::mpi;
MPI_Comm kittie::comm;
int kittie::rank;

// ADIOS-related
int kittie::ngroups;
int kittie::nnames;
adios2::ADIOS* kittie::adios;
std::string kittie::myreading;
std::string kittie::Codename;
std::string kittie::writing = ".writing";
std::string kittie::reading = ".reading";
std::vector<std::string> kittie::_FileMethods {"bpfile", "bp", "bp3", "hdf5"};
std::vector<std::string> kittie::_MetaMethods {"bpfile", "bp", "bp2", "bp3", "bp4", "hdf5"};
std::vector<std::string> kittie::allreading;
std::vector<std::string> kittie::groupnames;
std::map<std::string, kittie::Coupler*> kittie::Couplers;
std::map<std::string, std::string> kittie::filenames;
std::map<std::string, std::string> kittie::setengines;
std::map<std::string, std::map<std::string, std::string>> kittie::setparams;

// @effis-timestep
bool kittie::stepinit;
bool kittie::AllStep;
int kittie::_StepNumber;
double kittie::_StepPhysical;
adios2::Engine kittie::StepEngine;
std::string kittie::StepGroupname;
std::vector<std::string> kittie::StepGroups;


std::map<std::string, kittie::Timer*> kittie::Timers;
std::string kittie::timingdir;


bool kittie::Exists(std::string filename)
{
	std::ifstream ifile(filename);
	bool good = ifile.good();
	ifile.close();
	return good;
}


void kittie::Touch(std::string filename)
{
	std::ofstream outfile;
	outfile.open(filename);
	outfile.close();
}




/*
void kittie::_buildyaml()
{
	const char* env_p = std::getenv("KITTIE_YAML_FILE");
	const char* env_n = std::getenv("KITTIE_NUM");
	std::string yamlfile(env_p);
	std::string num(env_n);
	YAML::Node buildyaml = YAML::LoadFile(yamlfile);
	//kittie::appname = buildyaml["appname"].as<std::string>() + "-" + num;
	kittie::ngroups = buildyaml["n"].as<int>();
	for (int i=0; i<kittie::ngroups; i++)
	{
		kittie::groupnames.push_back(buildyaml["groups"][i].as<std::string>());
	}
}
*/


void kittie::_groupsyaml()
{
	std::string name;
	bool UseStep;

	///std::string yamlfile = ".kittie-groups-" + kittie::appname + ".yaml";
	const char* env_n = std::getenv("KITTIE_NUM");
	std::string num(env_n);
	std::string yamlfile = ".kittie-groups-" + num + ".yaml";

	// Probably not necessary but just to be safe
	kittie::filenames.clear();
	kittie::setengines.clear();
	kittie::setparams.clear();

	YAML::Node groupsyaml;
	YAML::Node params;
	std::map<std::string, std::string> param;

	if(Exists(yamlfile))
	{
		groupsyaml = YAML::LoadFile(yamlfile);
		kittie::timingdir = groupsyaml[".timingdir"].as<std::string>();
		groupsyaml.remove(".timingdir");

		for(YAML::const_iterator it=groupsyaml.begin(); it!=groupsyaml.end(); ++it)
		{
			param.clear();
			name = it->first.as<std::string>();

			if (groupsyaml[name]["filename"])
			{
				kittie::filenames[name] = groupsyaml[name]["filename"].as<std::string>();
			}
			if (groupsyaml[name]["engine"])
			{
				kittie::setengines[name] = groupsyaml[name]["engine"].as<std::string>();
			}
			if (groupsyaml[name]["params"])
			{
				params = groupsyaml[name]["params"];
				for(YAML::const_iterator pit=params.begin(); pit!=params.end(); ++pit)
				{
					param[pit->first.as<std::string>()] = pit->second.as<std::string>();
				}
				kittie::setparams[name] = param;
			}

			// @effis-timestep linked groups
			UseStep = groupsyaml[name]["AddStep"].as<bool>();
			if (UseStep)
			{
				kittie::StepGroups.push_back(name);
			}
		}
	}


}


void kittie::_codesyaml()
{
	std::string name;
	const char* env_n = std::getenv("KITTIE_NUM");
	std::string num(env_n);
	std::string yamlfile = ".kittie-codenames-" + num + ".yaml";

	YAML::Node codesyaml;
	YAML::Node codes;
	std::string thisname;

	if(Exists(yamlfile))
	{
		codesyaml = YAML::LoadFile(yamlfile);
		codes = codesyaml["codes"];
		kittie::Codename = codesyaml["codename"].as<std::string>();
		kittie::myreading = kittie::reading + "-" + kittie::Codename;
		for(std::size_t i=0; i<codes.size(); i++)
		{
			thisname = kittie::reading + "-" + codes[i].as<std::string>();
			kittie::allreading.push_back(thisname);
		}
	}
	else
	{
		kittie::myreading = kittie::reading;
		kittie::allreading.push_back(kittie::myreading);
	}

}


void kittie::_yaml_setup()
{
	// @effis-timestep into all EFFIS groups -- for now this is always false, but I'll have a switch for it
	kittie::AllStep = false;

	//kittie::_buildyaml();
	kittie::_groupsyaml();
	kittie::_codesyaml();

	// @effis-timestep
	kittie::stepinit = false;
	kittie::StepGroupname = kittie::Codename + "-step";
}


#ifdef USE_MPI
	void kittie::initialize(const std::string &filename, MPI_Comm comm, const bool DebugMode)
	{
		kittie::adios = new adios2::ADIOS(filename, comm, DebugMode);
		kittie::mpi = true;
		int err = MPI_Comm_dup(comm, &kittie::comm);
		err = MPI_Comm_rank(kittie::comm, &kittie::rank);
		kittie::_yaml_setup();
	}
	
	void kittie::initialize(MPI_Comm comm, const bool DebugMode)
	{
		kittie::adios = new adios2::ADIOS(comm, DebugMode);
		kittie::mpi = true;
		int err = MPI_Comm_dup(comm, &kittie::comm);
		err = MPI_Comm_rank(kittie::comm, &kittie::rank);
		kittie::_yaml_setup();
	}
#else
	void kittie::initialize(const std::string &filename, const bool DebugMode)
	{
		MPI_Comm dummy;
		kittie::adios = new adios2::ADIOS(filename, DebugMode);
		kittie::mpi = false;
		int err = MPI_Comm_dup(dummy, &kittie::comm);
		err = MPI_Comm_rank(kittie::comm, &kittie::rank);
		kittie::_yaml_setup();
	}
	
	void kittie::initialize(const bool DebugMode)
	{
		MPI_Comm dummy;
		kittie::adios = new adios2::ADIOS(DebugMode);
		kittie::mpi = false;
		int err = MPI_Comm_dup(dummy, &kittie::comm);
		err = MPI_Comm_rank(kittie::comm, &kittie::rank);
		kittie::_yaml_setup();
	}
#endif


void kittie::finalize() 
{

	for(std::map<std::string, kittie::Coupler*>::iterator it=kittie::Couplers.begin(); it!=kittie::Couplers.end(); ++it)
	{
		if (it->second->mode == adios2::Mode::Write)
		{

			std::string fname = it->second->filename + ".done";
			it->second->close();
			if (kittie::rank == 0)
			{
				kittie::Touch(fname);
			}
		}
	}

	if (kittie::stepinit)
	{
		std::ofstream outfile;
		outfile.open(kittie::StepGroupname + ".done");
		outfile << kittie::_StepNumber;
		outfile.close();

		kittie::StepEngine.Close();
	}

	delete kittie::adios;
}


// @effis-timestep inserts this
void kittie::write_step(double physical, int number)
{
	if (kittie::rank == 0)
	{
		kittie::_StepPhysical = physical;
		kittie::_StepNumber   = number;

		if (!kittie::stepinit)
		{
			adios2::IO io = kittie::declare_io(kittie::StepGroupname);
			adios2::Variable<int> VarNumber = io.DefineVariable<int>("StepNumber");
			adios2::Variable<double> VarStep = io.DefineVariable<double>("StepPhysical");
			//io.SetEngine("SST");
			//io.SetParameter("MarshalMethod", "bp");
			//io.SetParameter("RendezvousReaderCount", "0");
			//io.SetParameter("QueueLimit", "1");
			//io.SetParameter("QueueFullPolicy", "Discard");

#			ifdef USE_MPI
				kittie::StepEngine = io.Open(kittie::StepGroupname + ".bp", adios2::Mode::Write, MPI_COMM_SELF);
#			else
				kittie::StepEngine = io.Open(kittie::StepGroupname + ".bp", adios2::Mode::Write);
#			endif

			kittie::stepinit = true;
		}

		kittie::StepEngine.BeginStep();
		kittie::StepEngine.Put<int>("StepNumber", &kittie::_StepNumber);
		kittie::StepEngine.Put<double>("StepPhysical", &kittie::_StepPhysical);
		kittie::StepEngine.EndStep();
	}
}


adios2::IO kittie::declare_io(const std::string groupname)
{
	adios2::IO* io = new adios2::IO;
	*io = kittie::adios->DeclareIO(groupname);
	kittie::Couplers.insert(std::make_pair(groupname, new kittie::Coupler(groupname)));
	kittie::Couplers[groupname]->io = io;

	if ( kittie::setengines.find(groupname) != kittie::setengines.end() )
	{
		io->SetEngine(setengines[groupname]);
		for(std::map<std::string, std::string>::iterator it=kittie::setparams[groupname].begin(); it!=kittie::setparams[groupname].end(); ++it)
		{
			io->SetParameter(it->first, it->second);
		}
	}

	// @effis-timestep
	kittie::Couplers[groupname]->FindStep = false;

	return *(kittie::Couplers[groupname]->io);
}


// @effis-timestep -- Can't DefineVariables in DeclareIO b/c don't know read/write mode
void kittie::Coupler::AddStep()
{
	if (!FindStep && (std::find(kittie::StepGroups.begin(), kittie::StepGroups.end(), groupname) != kittie::StepGroups.end() || kittie::AllStep))
	{
		FindStep = true;
		if ((mode == adios2::Mode::Write) && (kittie::rank == 0))
		{
			adios2::Variable<int> VarNumber  = io->DefineVariable<int>("_StepNumber");
			adios2::Variable<double> VarStep = io->DefineVariable<double>("_StepPhysical");
		}
	}

	if (FindStep && (mode == adios2::Mode::Write) && (kittie::rank == 0))
	{
		engine.Put<int>("_StepNumber", kittie::_StepNumber);
		engine.Put<double>("_StepPhysical", kittie::_StepPhysical);
	}
}


adios2::Engine kittie::_mopen(const std::string groupname, const std::string filename, const adios2::Mode mode, MPI_Comm comm)
{
	kittie::Couplers[groupname]->_open(comm, filename, mode);
	return kittie::Couplers[groupname]->engine;
}


adios2::Engine kittie::open(const std::string groupname, const std::string filename, const adios2::Mode mode)
{
	return kittie::_mopen(groupname, filename, mode, kittie::comm);
}


#ifdef USE_MPI
	adios2::Engine kittie::open(const std::string groupname, const std::string filename, const adios2::Mode mode, MPI_Comm comm)
	{
		return kittie::_mopen(groupname, filename, mode, comm);
	}
#endif



/* Coupler class */

void kittie::Coupler::_open(MPI_Comm incomm, const std::string infilename, const adios2::Mode inmode)
{
	if (!init)
	{
		mode = inmode;
		CurrentStep = -1;
		MPI_Comm_dup(incomm, &comm);
		int err = MPI_Comm_rank(comm, &rank);
		_lockfile();
	}
	
	if (!opened)
	{
		// Moved this block so different files can be used per step for same group
		if (kittie::filenames.find(groupname) !=  kittie::filenames.end())
		{
			filename = kittie::filenames[groupname];
		}
		else
		{
			filename = infilename;
		}
		
		cwriting = filename + kittie::writing;
		creading = filename + kittie::myreading;
		allcreading.clear();
		for(std::size_t i=0; i<kittie::allreading.size(); i++)
		{
			allcreading.push_back(filename + kittie::allreading[i]);
		}

		// This will wait for the file to exist if reading
		_CoupleOpen();
	}
}


kittie::Coupler::Coupler(const std::string ingroupname)
{
	init = false;
	opened = false;
	groupname = ingroupname;
}


//kittie::Coupler::~Coupler(){}


void kittie::Coupler::Until_Nonexistent_Write()
{
	kittie::Touch(cwriting);
	bool exists;
	for(std::size_t i=0; i<allcreading.size(); i++)
	{
		exists = true;
		while (exists)
		{
			exists = kittie::Exists(allcreading[i]);
		}
	}
}


void kittie::Coupler::Until_Nonexistent_Read(int verify_level)
{
	bool redo = false;
	bool exists = true;
	while(exists)
	{
		exists = kittie::Exists(cwriting);
	}
	kittie::Touch(creading);

	for (int i=0; i<verify_level; i++)
	{
		if (kittie::Exists(cwriting))
		{
			std::remove(creading.c_str());
			redo = true;
			break;
		}
	}

	if (redo)
	{
		Until_Nonexistent_Read(verify_level);
	}
}



void kittie::Coupler::AcquireLock()
{
	if (rank == 0)
	{
		if (mode == adios2::Mode::Read)
		{
			//while (! kittie::Exists(filename))
			//{
			//	continue;
			//}
			Until_Nonexistent_Read();
		}
		else if (mode == adios2::Mode::Write)
		{
			Until_Nonexistent_Write();
		}

		//UntilNonexistent();
	}
	int err = MPI_Barrier(comm);
}


void kittie::Coupler::ReleaseLock()
{
	int err = MPI_Barrier(comm);
	if (rank == 0)
	{
		if (mode == adios2::Mode::Write)
		{
			std::remove(cwriting.c_str());
		}
		else if (mode == adios2::Mode::Read)
		{
			std::remove(creading.c_str());
		}
	}
}


void kittie::Coupler::_CoupleOpen()
{

	if (mode == adios2::Mode::Read)
	{
		WaitDataExistence();
	}

	if (LockFile)
	{
		AcquireLock();
	}

#	ifdef USE_MPI
		engine = io->Open(filename, mode, comm);
#	else
		engine = io->Open(filename, mode);
#	endif

	if (LockFile)
	{
		ReleaseLock();
	}

	opened = true;
}

void kittie::Coupler::WaitDataExistence()
{
	std::string EngineType = io->EngineType();
	std::transform(EngineType.begin(), EngineType.end(), EngineType.begin(), ::tolower);
	bool wait = (std::find(kittie::_MetaMethods.begin(), kittie::_MetaMethods.end(), EngineType) != kittie::_MetaMethods.end());
	if (wait)
	{
		while (! kittie::Exists(filename + "/md.idx"))
		{
			continue;
		}
		while (! kittie::Exists(filename + "/md.0"))
		{
			continue;
		}
	}
}

void kittie::Coupler::_lockfile()
{
	std::string EngineType = io->EngineType();
	std::transform(EngineType.begin(), EngineType.end(), EngineType.begin(), ::tolower);
	LockFile = (std::find(kittie::_FileMethods.begin(), kittie::_FileMethods.end(), EngineType) != kittie::_FileMethods.end());
}


void kittie::Coupler::begin_write()
{
	//if (!init)
	if (!opened)
	{
		_CoupleOpen();
	}
	engine.BeginStep(adios2::StepMode::Append);
}


adios2::StepStatus kittie::Coupler::FileSeek(bool &found, const int step, const double timeout)
{
	adios2::StepStatus status;
	int current_step = -1;

	WaitDataExistence();
	AcquireLock();
	if (!opened)
	{
#		ifdef USE_MPI
			engine = io->Open(filename, mode, comm);
#		else
			engine = io->Open(filename, mode);
#		endif

		opened = true;
	}

	while (true)
	{
#		if ADIOS2_VERSION_MAJOR > 2 || (ADIOS2_VERSION_MAJOR == 2 && ADIOS2_VERSION_MINOR > 3)
			status = engine.BeginStep(adios2::StepMode::Read, timeout);
#		else
			status = engine.BeginStep(adios2::StepMode::NextAvailable, timeout);
#		endif


		if (status == adios2::StepStatus::OK)
		{
			current_step = current_step + 1;
		}
		else
		{
			break;
		}

		if (current_step == step)
		{
			found = true;
			CurrentStep++;
			break;
		}

		engine.EndStep();
	}

	ReleaseLock();
	if (!found)
	{
		engine.Close();
		opened = false;
		io->RemoveAllVariables();
		io->RemoveAllAttributes();
		if (!kittie::Exists(filename + ".done"))
		{
			status = adios2::StepStatus::NotReady;
		}
	}

	return status;
}


adios2::StepStatus kittie::Coupler::begin_step(const double timeout)
{
	adios2::StepStatus status;

	if (mode == adios2::Mode::Write)
	{
		begin_write();
		status = adios2::StepStatus::OK;
	}

	else if (mode == adios2::Mode::Read)
	{
		//std::cerr << "If reading from file for coupling, must give what step you want to read from\n";
		//abort();
		
		status = begin_step(CurrentStep+1, timeout);
	}

	init = true;

	return status;
}


adios2::StepStatus kittie::Coupler::begin_step(const int step, const double timeout)
{
	bool found = false;
	adios2::StepStatus status;

	if (mode == adios2::Mode::Write)
	{
		begin_write();
		status = adios2::StepStatus::OK;
	}
	
	else if (mode == adios2::Mode::Read)
	{
		if (LockFile)
		{
			while (!found)
			{
				status = FileSeek(found, step, timeout);
				if (timeout > -1.0)
				{
					break;
				}
			}
		}

		else
		{
			// This block shouldn't really be necessary with proper ADIOS
			//if (!init)
			if (!opened)
			{
				_CoupleOpen();
			}
#			if ADIOS2_VERSION_MAJOR > 2 || (ADIOS2_VERSION_MAJOR == 2 && ADIOS2_VERSION_MINOR > 3)
				status = engine.BeginStep(adios2::StepMode::Read, timeout);
#			else
				status = engine.BeginStep(adios2::StepMode::NextAvailable, timeout);
#			endif
		}
	}

	init = true;
	return status;
}


void kittie::Coupler::end_step()
{
	// @effis-timestep added if needed
	AddStep();

	if (LockFile)
	{
		AcquireLock();
	}

	engine.EndStep();

	if (LockFile)
	{
		ReleaseLock();
		if (mode == adios2::Mode::Read)
		{
			engine.Close();
			opened = false;
			io->RemoveAllVariables();
			io->RemoveAllAttributes();;
		}
	}
}


void kittie::Coupler::close()
{
	if (opened) 
	{
		if ((mode == adios2::Mode::Write) && LockFile)
		{
			AcquireLock();
		}
		engine.Close();
		opened = false;
		if ((mode == adios2::Mode::Write) && LockFile)
		{
			ReleaseLock();
		}
	}
}


kittie::Timer::Timer()
{
	stop = -1;
	start = -1;
}


#ifdef USE_MPI
	void kittie::start_timer(std::string name, MPI_Comm comm)
	{
		std::string timefile;
		int rank, size, ierr;
		std::size_t tdims, toffs, tlocs;

		bool found = (kittie::Timers.find(name) != kittie::Timers.end());
		if (!found)
		{
			kittie::Timers.insert(std::make_pair(name, new kittie::Timer));
		}

		if (!found)
		{
			kittie::Timers[name]->io = kittie::adios->DeclareIO(name);
			ierr = MPI_Comm_rank(comm, &rank);
			ierr = MPI_Comm_size(comm, &size);
			tdims = size;
			toffs = rank;
			tlocs = 1;
			adios2::Variable<double> varid = kittie::Timers[name]->io.DefineVariable<double>("time", {tdims}, {toffs}, {tlocs}, adios2::ConstantDims);
			timefile = kittie::timingdir + "/" + name + ".bp";
			kittie::Timers[name]->engine = kittie::Timers[name]->io.Open(timefile, adios2::Mode::Write, comm);
		}
		kittie::Timers[name]->start = MPI_Wtime();
	}
#endif


void kittie::start_timer(std::string name)
{
#	ifndef USE_MPI
		std::cerr << "Need MPI to use EFFIS timers from C++" << std::endl;
		return;
#	endif
		kittie::start_timer(name, kittie::comm);
}


void kittie::stop_timer(std::string name)
{
	double diff[1];
	bool found = (kittie::Timers.find(name) != kittie::Timers.end());
	if (found)
	{
		if (kittie::Timers[name]->start > kittie::Timers[name]->stop)
		{
			kittie::Timers[name]->stop = MPI_Wtime();
			diff[0] = kittie::Timers[name]->stop - kittie::Timers[name]->start;
			adios2::Variable<double> varid = kittie::Timers[name]->io.InquireVariable<double>("time");
			kittie::Timers[name]->engine.BeginStep();
			kittie::Timers[name]->engine.Put(varid, diff);
			kittie::Timers[name]->engine.EndStep();
			kittie::Timers[name]->start = kittie::Timers[name]->stop;
		}
		else
		{
			std::cerr << "Found stop without matching start for timer " + name << std::endl;
		}

	}

	else
	{
		std::cerr << "Found stop without matching start for timer " + name << std::endl;
	}
}
	

