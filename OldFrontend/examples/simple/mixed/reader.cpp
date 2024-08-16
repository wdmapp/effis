#include "adios2.h"
#include <mpi.h>
#include <thread>
#include <chrono>
#include <iostream>

int main(int argc, char **argv)
{
	MPI_Comm comm;
	int rank, nproc;
	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	MPI_Comm_split(MPI_COMM_WORLD, 1, rank, &comm);
	MPI_Comm_rank(comm, &rank);
	MPI_Comm_size(comm, &nproc);

    //@effis-init comm=comm
	//adios2::ADIOS adios(comm, adios2::DebugON);

    //@effis-begin "Jabberwocky"->"Jabberwocky"
	adios2::IO reader_io = adios.DeclareIO("Jabberwocky");
	adios2::Engine reader = reader_io.Open("Jabberwocky.bp", adios2::Mode::Read, comm);
	std::vector<double> data;

    while (true)
	{
		adios2::StepStatus status = reader.BeginStep(adios2::StepMode::Read, 10.0);

        if (status == adios2::StepStatus::NotReady)
		{
            continue;
		}
		else if (status != adios2::StepStatus::OK)
		{
            break;
		}

		adios2::Variable<double> random = reader_io.InquireVariable<double>("RandomReals");
		adios2::Dims shape = random.Shape();

		const int s = 0;
		auto d1 = shape[0];
		auto d2 = shape[1];

		size_t dcount = (d2 / nproc);
		size_t dstart = rank * dcount;
		if (rank == nproc - 1)
		{
			dcount += d2 % nproc;
		}

		const::adios2::Dims start{0,  dstart};
		const::adios2::Dims count{d1, dcount};
		const adios2::Box<adios2::Dims> sel(start, count);
		random.SetSelection(sel);
		reader.Get(random, data);
        reader.EndStep();
		std::cout << "Read step: " << reader.CurrentStep() << std::endl;
	}

    reader.Close();
    //@effis-end
	//@effis-finalize
}
