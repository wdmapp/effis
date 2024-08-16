# Integration

The method by which one integrates EFFIS with their code is to first add the ADIOS APIs to save/read the desired data for their code. 
Then EFFIS pragmas, which amount to code comments, are added to markup the I/O-related code blocks.
At installation, one runs the EFFIS pre-processor on the repository, and these pragmas are translated to the appropriate code statements.
Let's look at some examples to understand.


## Code Pragmas 101

Here's the ADIOS [Gray-Scott ADIOS tutorial](https://github.com/suchyta1/adiosvm/tree/cpp/Tutorial/gray-scott),
which is a lightweight simulation of diffusion concentrations.
The output from the simulation is as shown below. EFFIS is integrated by adding the comments in the fold blocks.


<details><summary></summary>
<p style="margin-bottom:-0.5cm;">

```cpp
	//@effis-init xml="adios2.xml", comm=comm
```

</p>
<p style="margin-bottom:-1.2cm;"></p>
</details>

```cpp
    adios2::ADIOS adios(settings.adios_config, comm, adios2::DebugON);
	// setting.adios_config is the XML file
```


<p style="margin-bottom:-0.5cm;"></p>


<details><summary></summary>
<p style="margin-bottom:-0.5cm;">

```cpp
	//@effis-begin "SimulationOutput"->"ConcentrationData"
```

</p>
<p style="margin-bottom:-1.2cm;"></p>
</details>

```cpp
    adios2::IO io = adios.DeclareIO("SimulationOutput");

    io.DefineAttribute<double>("F", settings.F);
    io.DefineAttribute<double>("k", settings.k);
    io.DefineAttribute<double>("dt", settings.dt);
    io.DefineAttribute<double>("Du", settings.Du);
    io.DefineAttribute<double>("Dv", settings.Dv);
    io.DefineAttribute<double>("noise", settings.noise);

    adios2::Variable<double> varU = io.DefineVariable<double>(
        "U", {sim.npz * sim.size_z, sim.npy * sim.size_y, sim.npx * sim.size_x},
        {sim.pz * sim.size_z, sim.py * sim.size_y, sim.px * sim.size_x},
        {sim.size_z, sim.size_y, sim.size_x});

    adios2::Variable<double> varV = io.DefineVariable<double>(
        "V", {sim.npz * sim.size_z, sim.npy * sim.size_y, sim.npx * sim.size_x},
        {sim.pz * sim.size_z, sim.py * sim.size_y, sim.px * sim.size_x},
        {sim.size_z, sim.size_y, sim.size_x});

    adios2::Variable<int> varStep = io.DefineVariable<int>("step");

    adios2::Engine writer = io.Open(settings.output, adios2::Mode::Write);

    for (int i = 0; i < settings.steps; i++) {
        sim.iterate();

        if (i % settings.plotgap == 0) {
            std::vector<double> u = sim.u_noghost();
            std::vector<double> v = sim.v_noghost();

            writer.BeginStep();
            writer.Put<int>(varStep, &i);
            writer.Put<double>(varU, u.data());
            writer.Put<double>(varV, v.data());
            writer.EndStep();
        }
    }

    writer.Close();
```


<p style="margin-bottom:-0.5cm;"></p>


<details><summary></summary>
<p style="margin-bottom:-1.0cm;">

```cpp
	//@effis-end
```

</p>
</details>



<p style="margin-bottom:1.0cm;"></p>

The first EFFIS comment is:

```cpp
	//@effis-init xml="adios2.xml", comm=comm
```

EFFIS has separate initialization from ADIOS, so you can use EFFIS side by side ordinary ADIOS in your code; some blocks using EFFIS, others not.
This way, you don't have to update every ADIOS block with EFFIS pragmas all at once.
The XML file is not required, (and any equivalent setting from the YAML config file take precedence over the code-level XML file).
`comm` is required when using MPI, which will very likely be most often.


The second EFFIS comment is:

```cpp
	//@effis-begin "SimulationOutput"->"ConcentrationData"
```

This says, lets use ADIOS I/O group "SimulationOutput" and label it as "ConcentrationData" in EFFIS. 
When we run the pre-processor, all the I/O operations in this block belonging to originally named group "SimulationOutput"
will be updated to add the extra features provided by EFFIS, and these features will be controlled in EFFIS with the label "ConcentrationData",
i.e. the EFFIS grouping name is what we will use in the EFFIS config file.
(The original/EFFIS names could be the same, I just made them different to show that we can do that if desired.)

The final EFFIS comment ends the replacement block:

```cpp
	//@effis-end
```


## Code Pragmas 102

Now let's make things a little more interesting. Here is a reader for the Gray-Scott example which calculates a PDF then writes it out.



<details><summary></summary>
<p style="margin-bottom:-0.5cm;">

``` cpp
    // adios2 variable declarations
    adios2::Variable<double> var_u_in, var_v_in;
    adios2::Variable<int> var_step_in;
    adios2::Variable<double> var_u_pdf, var_v_pdf;
    adios2::Variable<double> var_u_bins, var_v_bins;
    adios2::Variable<int> var_step_out;
    adios2::Variable<double> var_u_out, var_v_out;
```

</p>
<p style="margin-bottom:-0.5cm;"></p>
</details>



``` cpp
	//@effis-init xml="adios2.xml", comm=comm
    adios2::ADIOS ad ("adios2.xml", comm, adios2::DebugON);


    // IO objects for reading and writing
	
	//@effis-begin reader_io-->"ConcentrationData"; writer--->"PDFData"
    adios2::IO reader_io = ad.DeclareIO("SimulationOutput");
    adios2::IO writer_io = ad.DeclareIO("PDFAnalysisOutput");
```

<p style="margin-bottom:-0.5cm;"></p>

<details><summary></summary>
<p style="margin-bottom:-0.0cm;">

```cpp
    if (!rank) 
    {
        std::cout << "PDF analysis reads from Simulation using engine type:  " << reader_io.EngineType() << std::endl;
        std::cout << "PDF analysis writes using engine type:                 " << writer_io.EngineType() << std::endl;
    }
```

</p>
<p style="margin-bottom:-0.5cm;"></p>
</details>


```cpp
    // Engines for reading and writing
    adios2::Engine reader = reader_io.Open(in_filename, adios2::Mode::Read, comm);
    adios2::Engine writer = writer_io.Open(out_filename, adios2::Mode::Write, comm);

    bool shouldIWrite = (!rank || reader_io.EngineType() == "HDF5");

    // read data per timestep
	int kstep = 0;
    int stepAnalysis = 0;
    while(true) {

        // Begin step
        adios2::StepStatus read_status = reader.BeginStep(adios2::StepMode::NextAvailable, 10.0f);

        if (read_status == adios2::StepStatus::NotReady)
        {
            // std::cout << "Stream not ready yet. Waiting...\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));
            continue;
        }
        else if (read_status != adios2::StepStatus::OK)
        {
            break;
        }
 
        int stepSimOut = reader.CurrentStep();
		kstep++;
```

Here, we see that we can markup multiple I/Os in the same code area, where the different sections are separated by a `;`.
We can also define the pragmas in terms of original `adios2::IO` or `adios2::Engine` objects instead of the original names.
(But we still use a name for reference within the EFFIS features.)
Notice that the `reader_io` is linked with the same group we wrote out in the writer.

The reader could also has a `step` tag, which tells us what step we want to read from the input.
It's not really necessary in thins example for memory based transport (e.g. SST, InSituMPI) -- we look for a new step, wait if we don't find anything,
and abort when the status is no longer valid. 
In ADIOS, steps append to files, but there isn't a native ADIOS-only way to safely seek through these files files while they're still open,
(At least not in a concise way; you have to do things like like for lock files or write each step to a separate file.)

There's nothing else specific that I'll point about about the remainder of the code, but it's included below.

<details><summary></summary>
<p style="margin-bottom:-0.5cm;">

```cpp
        // Inquire variable and set the selection at the first step only
        // This assumes that the variable dimensions do not change across timesteps

        // Inquire variable
        var_u_in = reader_io.InquireVariable<double>("U");
        var_v_in = reader_io.InquireVariable<double>("V");
        var_step_in = reader_io.InquireVariable<int>("step");

        

        std::pair<double, double> minmax_u =  var_u_in.MinMax();
        std::pair<double, double> minmax_v =  var_v_in.MinMax();

        shape = var_u_in.Shape();

        // Calculate global and local sizes of U and V
        u_global_size = shape[0] * shape[1] * shape[2];
        u_local_size  = u_global_size/comm_size;
        v_global_size = shape[0] * shape[1] * shape[2];
        v_local_size  = v_global_size/comm_size;

        size_t count1 = shape[0]/comm_size;
        size_t start1 = count1 * rank;
        if (rank == comm_size-1) {
            // last process need to read all the rest of slices
            count1 = shape[0] - count1 * (comm_size - 1);
        }

        /*std::cout << "  rank " << rank << " slice start={" <<  start1 
            << ",0,0} count={" << count1  << "," << shape[1] << "," << shape[2]
            << "}" << std::endl;*/

        // Set selection
        var_u_in.SetSelection(adios2::Box<adios2::Dims>(
                    {start1,0,0},
                    {count1, shape[1], shape[2]}));
        var_v_in.SetSelection(adios2::Box<adios2::Dims>(
                    {start1,0,0},
                    {count1, shape[1], shape[2]}));

        // Declare variables to output
        if (firstStep) {
            var_u_pdf = writer_io.DefineVariable<double> ("U/pdf",
                    { shape[0], nbins },
                    { start1, 0 },
                    { count1, nbins } );
            var_v_pdf = writer_io.DefineVariable<double> ("V/pdf",
                    { shape[0], nbins },
                    { start1, 0},
                    { count1, nbins } );

            if (shouldIWrite)
            {
                var_u_bins = writer_io.DefineVariable<double> ("U/bins",
                        { nbins }, { 0 }, { nbins } );
                var_v_bins = writer_io.DefineVariable<double> ("V/bins",
                        { nbins }, { 0 }, { nbins } );
                var_step_out = writer_io.DefineVariable<int> ("step");
            }


            if ( write_inputvars) {
                var_u_out = writer_io.DefineVariable<double> ("U",
                        { shape[0], shape[1], shape[2] },
                        { start1, 0, 0 },
                        { count1, shape[1], shape[2] } );
                var_v_out = writer_io.DefineVariable<double> ("V",
                        { shape[0], shape[1], shape[2] },
                        { start1, 0, 0 },
                        { count1, shape[1], shape[2] } );

            }
            firstStep = false;
        }
```

</p>
<p style="margin-bottom:-0.5cm;"></p>
</details>


<p style="margin-bottom:-0.5cm;"></p>


``` cpp
        // Read adios2 data
        reader.Get<double>(var_u_in, u);
        reader.Get<double>(var_v_in, v);
        if (shouldIWrite)
        {
            reader.Get<int>(var_step_in, &simStep);
        }

        // End adios2 step
        reader.EndStep();
```


<p style="margin-bottom:-0.5cm;"></p>



<details><summary></summary>
<p style="margin-bottom:-0.5cm;">

```

        if (!rank)
        {
            std::cout << "PDF Analysis step " << stepAnalysis
                << " processing sim output step "
                << stepSimOut << " sim compute step " << simStep << std::endl;
        }


        // HDF5 engine does not provide min/max. Let's calculate it
        if (reader_io.EngineType() == "HDF5")
        {
            auto mmu = std::minmax_element(u.begin(), u.end());
            minmax_u = std::make_pair(*mmu.first, *mmu.second);
            auto mmv = std::minmax_element(v.begin(), v.end());
            minmax_v = std::make_pair(*mmv.first, *mmv.second);
        }
```

</p>
<p style="margin-bottom:-0.5cm;"></p>
</details>




``` cpp
        // Compute PDF
        std::vector<double> pdf_u;
        std::vector<double> bins_u;
        compute_pdf(u, shape, start1, count1, nbins, minmax_u.first, minmax_u.second, pdf_u, bins_u);

        std::vector<double> pdf_v;
        std::vector<double> bins_v;</p>

        compute_pdf(v, shape, start1, count1, nbins, minmax_v.first, minmax_v.second, pdf_v, bins_v);

        // write U, V, and their norms out
        writer.BeginStep ();
        writer.Put<double> (var_u_pdf, pdf_u.data());
        writer.Put<double> (var_v_pdf, pdf_v.data());
        if (shouldIWrite)
        {
            writer.Put<double> (var_u_bins, bins_u.data());
            writer.Put<double> (var_v_bins, bins_v.data());
            writer.Put<int> (var_step_out, simStep);
        }
        if (write_inputvars) {
            writer.Put<double> (var_u_out, u.data());
            writer.Put<double> (var_v_out, v.data());
        }
        writer.EndStep ();
        ++stepAnalysis;
    }

    // cleanup

    reader.Close();
    writer.Close();
	//@effis-end
```
