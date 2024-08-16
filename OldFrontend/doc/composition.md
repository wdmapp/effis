# Job Composition

Job composition in EFFIS is done through a YAML configuration file. Let's start with an example that runs a single code.

```yaml
# Top-level job settings
jobname: xgc-DIIID                    # jobname: Sets the job name for scheduler
walltime: 7200                        # walltime: Wall time to request for job (in seconds)
rundir: /dir/to/job/output            # rundir: Top directory for job output


# Site-specific submissions settings
machine:
  name: summit                        # name: Platform where workflow runs
  charge: fus123                      # charge: Account to charge node-hours
  

# What codes to run and how
run:
  xgc:
    processes: 48                     # processes: Number of MPI ranks
    processes-per-node: 6             # processes-per-node: Number of MPI ranks per node
    cpus-per-process: 7               # cpus-per-processes: Number of cores per MPI rank 
    executable_path: /path/to/exe     # execuatable_path: File path of executable to run
```

Basically, the file is a set of keyword-value pairs, which looks like a Python dictionary. 
Ordering of the keywords throughout the file does not matter.
Most of the keywords in the example above are recongized by EFFIS as reserved names with a specific meaning.
Users can also define their own variables and dereference them, but let's return to that later.

The example runs an executable at *"/path/to/exe"* with 48 MPI ranks on Summit, 6 ranks per node, charged to account *fus123*.
The job output writes to *"/dir/to/job/output"*, with a subdirectory for each code's content. Here *xgc* is the only code,
so the job has a single execution subdirectory *"/dir/to/job/output/xgc"*. *xgc* is just a label from the EFFIS perspective;
it could be renamed to anything, and the subdirectory would take on the new name. *run* is the EFFIS-reserved keyword to demarcate
the section listing the different codes. Similarly, *machine* marks a scope for site-specific submission settings.

Different EFFIS-recognized keywords exist in the different composition scopes, with
three basic scopes/sections in the EFFIS YAML file: 
[top-level job settings](#recognized-keywords-in-top-level-scope),
[site-specific submissions settings](#recognized-keywords-in-machine-scope) (under *machine*), and
[what codes to run and how](#recognized-keywords-in-code-scope) (under *run*).
The recongized keywords in each of the scopes are itemized below. More example usage will follow.


### Recognized keywords in top-level scope

- *jobname*: How to set the job name for scheduler
- *walltime*: Wall time to request for job (in seconds)
- *rundir*: Top directory for job output
- *include*: Import YAML entries from another file(s)
- *share*: Included codes are launched on same nodes
- *env*: Environment variables to define
- *pre-submit-commands*: Run these commands in *rundir* (during composition, i.e. before submission)
- *copy-contents*: Copy files/directories in the given directory to *rundir* (during composition, i.e. before submission)
- *copy*: Like copy contents, but copy precisely what is given, not what is under it
- *link*: Make a symbolic link to what’s given
- *file-edit*: Regular expression editing of the given files

### Recognized keywords in machine scope

- *name*: name
- *charge*: account to charge node-hours
- *queue*: specify queue partition when multiple are available
- *job_setup*: shell script to run on service node before the main executables launch, as if in the scheduler submission file – setup modules, etc.
- *submit_setup*: shell script to run on login node, at composition time, i.e. before submission
- *scheduler_args*: additional settings to give to MPI launcher

### Recognized keywords in code scope

- *execuatable_path*: file path of executable to run
- *processes*: number of MPI ranks
- *cpus-per-processes*: cores per MPI rank (will be renamed to cores-per-processes)
- *use_gpus*: turn on GPUs
- *commandline_args*: command line arguments to pass
- *commandline_options*: --key value style command line options to pass
- *env*: environment variables to define
- *pre-submit-commands*: Run these commands in the code's subdirectory
- *copy-contents*: Copy files in the given directory to the code's subdirectory (during composition, i.e. before submission)
- *copy*: Like copy contents, but copy precisely what is given, not what is under it
- *link*: Make a symbolic link to what’s given
- *file-edit*: Regular expression editing of the given files


## User-defined variables

Users can define their own variables and dereference them anywhere in the file; order doesn’t matter.
`${<keyword>}` is used to retrieve values (and can be used with EFFIS-reserved keywords too, if desired).

```yaml
twohr: 7200
walltime: ${twohr}
```


## Adding to the example

The first example above was fairly basic, and in particular, did not make use of any of the keywords
that help setup a job's input and environment. Here, directories are created, several copies made,
an input file edited, an environment variable defined, etc. The machine setup also demonstrates more.

```yaml
jobname: xgc-DIIID
walltime: 7200
rundir: /dir/to/job/output
copy:
  - [whatever.txt, file1.txt]     # Copies whatever.txt to /dir/to/job/output/file1
  - file2.txt                     # Copies    file2.txt to /dir/to/job/output/file2

prev: /restart/from/here          # User-defined value, here used to setup from restart as an example
prev-step: 01000                  # User-defined value, here used to setup from restart as an example

machine:
  name: theta
  charge: abc456
  queue: default
  job_setup: ./modules.sh               # Shell script to run after submission, on service node       
  scheduler_args: “-p SUCHYTA_DOMAIN”   # Extra options to give to MPI runner

run:
  xgc:
    processes: 48
    processes-per-node: 6
    cpus-per-process: 7
    executable_path: /path/to/xgc

    env:
      OMP_NUM_THREADS: 14         # xgc runs with this enviromnent variable defined
    pre-submit-commands:
      - "mkdir restart_dir"       # Creates /dir/to/job/output/xgc/restart_dir
      - "mkdir timing"            # Creates /dir/to/job/output/xgc/timing
      
    copy-contents:
      - /path/to/input/files      # Everything in /path/to/input/files is copied to /dir/to/job/output/xgc
    copy:
      - ${prev}/timestep.dat      # Copies /restart/from/here/timestep.dat to /dir/to/job/output/xgc/timestep.dat
    link:
      - - ${prev}/restart_dir/xgc.restart.${prev-steps}.bp      #  Links /restart/from/here/restart_dir/xgc.restart.01000.bp
        - restart_dir/xgc.restart.${prev-steps}.bp              # to /dir/to/job/output/xgc/restart_dir/xgc.restart.01000.bp
        
    file-edit:
      input:
        - ['^\s*sml_restart\s*=.*$’, 'sml_restart=.true.']      # Regex edit file /dir/to/job/output/xgc/input
```


## Adding another process

To this point, the examples have only run a single application in the job.
Adding a second amounts to including another under the *run* section.
Here, *xgc* and *vtkm* run concurrently during the same job.

```yaml
rundir: /dir/to/job/output
setup: /input/files

run:
  xgc:
    processes: 48
    processes-per-node: 6
    cpus-per-process: 7
    executable_path: ./xgc-es
    copy-contents:
      - /${setup}/xgc-DIIID-input/
    pre-submit-commands:
      - "mkdir restart_dir"
      - "mkdir timing"
      
  vtkm:
    processes: 1
    cpus-per-process: 21
    executable_path: ./AvocadoVTKm
    pre-submit-commands: ["mkdir output"]
    copy:
      - ${setup}/xgc-DIIID-input/dave.xml
    env:
      OMP_NUM_THREADS: 21
      
    # Will ultimately call: ./AvocadoVTKm --openmp --geom D3D --imageDir output
    commandline_options:  # options add --key value
      geom: D3D
      imageDir: output
    commandline_args:     # args add whatever is explicitly listed
      - --openmp
```


## Connecting producers and consumers (coupling)

While it is not required between multiple applications, there is also EFFIS-aware coupling.

```yaml
rundir: /dir/to/job/output
setup: /input/files

run:
  xgc:
    processes: 48
    processes-per-node: 6
    cpus-per-process: 7
    executable_path: ./xgc-es
    copy-contents:
      - /${setup}/xgc-DIIID-input/
    pre-submit-commands:
      - "mkdir restart_dir"
      - "mkdir timing"
      
    .field3D:
      output_path: xgc.3d.bp
      adios_engine: BP4
      adios_engine_params:
        OpenTimeSecs: 3000
    .diagnosis.mesh:
      output_path: xgc.mesh.bp
    .diagnosis.1d:
      output_path: xgc.oneddiag.bp
      adios_engine: SST

      
  vtkm:
    processes: 1
    cpus-per-process: 21
    executable_path: ./AvocadoVTKm
    pre-submit-commands: ["mkdir output"]
    copy:
      - ${setup}/xgc-DIIID-input/dave.xml
    env:
      OMP_NUM_THREADS: 21
      
    # Will ultimately call: ./AvocadoVTKm --openmp --geom D3D --imageDir output
    commandline_options:  # options add --key value
      geom: D3D
      imageDir: output
    commandline_args:     # args add whatever is explicitly listed
      - --openmp
      
     .3d:
      reads: xgc.field3D
    .mesh:
      reads: xgc.diagnosis.mesh
    .oneddiag:
      reads: xgc.diagnosis.1d

```
