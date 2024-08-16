#include "adios2.h"
#include <mpi.h>
#include <cstdlib>
#include <thread>
#include <chrono>
#include <iostream>
#include <complex>

namespace coupler
{
	typedef std::complex<double> CV;
}

int main(int argc, char **argv)
{
    const std::size_t nelems = 10;
	int KnownInt, RandomInt, KnownInts[nelems], RandomInts[nelems];
	int GlobalDims[1], Offsets[1], LocalDims[1];

	coupler::CV KnownComplex[nelems];

	MPI_Comm comm;
	int rank, nproc;
	double dt=0.1;

	MPI_Init(&argc, &argv);
	MPI_Comm_dup(MPI_COMM_WORLD, &comm);
	MPI_Comm_rank(comm, &rank);
	MPI_Comm_size(comm, &nproc);


    //@effis-init comm=comm
	adios2::ADIOS adios(comm);

	for (int i=0; i<nelems; i++)
	{
		KnownInts[i] = i;
		KnownComplex[i] = (double) i * std::complex<double>(1.0, 1.0);
	}

    //@effis-begin "Jabberwocky"->"Jabberwocky"
	adios2::IO io = adios.DeclareIO("Jabberwocky");

    GlobalDims[0] = nproc * nelems;
    Offsets[0] = rank * nelems;
    LocalDims[0] = nelems;
	adios2::Variable<int> vKnownInts  = io.DefineVariable<int>("KnownInts",  {nproc*nelems}, {rank*nelems}, {nelems}, adios2::ConstantDims);
	adios2::Variable<coupler::CV> vKnownComplex  = io.DefineVariable<coupler::CV>("KnownComplex",  {nproc*nelems}, {rank*nelems}, {nelems}, adios2::ConstantDims);
    adios2::Variable<int> vRandomInts = io.DefineVariable<int>("RandomInts", {nproc*nelems}, {rank*nelems}, {nelems}, adios2::ConstantDims);

	adios2::Engine engine = io.Open("Jabberwocky.bp", adios2::Mode::Write, comm);

    for (int j=0; j<10; j++)
	{
		
		for (int i=0; i<nelems; i++)
		{
			RandomInts[i] = rand() % 1000;
		}
		
        //@effis-timestep physical=j*dt, number=j
        engine.BeginStep();
        engine.Put(vKnownInts,  KnownInts);
        engine.Put(vKnownComplex,  KnownComplex);
        engine.Put(vRandomInts, RandomInts);
        engine.EndStep();
		std::cout << "writer step: " << j << std::endl;

	}

    engine.Close();
    //@effis-end

    //@effis-finalize
}

