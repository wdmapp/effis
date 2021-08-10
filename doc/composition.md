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

The example runs an executable at `/path/to/exe` with 48 MPI ranks on Summit, 6 ranks per node, charged to account *fus123*.
The job output writes to `/dir/to/job/output`, with a subdirectory for each code's content. Here *xgc* is the only code,
so the job has a single execution subdirectory `/dir/to/job/output/xgc`. *xgc* is just a label from the EFFIS perspective;
it could be renamed to anything, and the subdirectory would take on the new name. *run* is the EFFIS-reserved keyword to demarcate
the section listing the different codes. Similarly, *machine* marks a scope for site-specific submission settings.

Different EFFIS-recognized keywords exist in the different composition scopes, with
three basic scopes/sections in the EFFIS YAML file: 
[top-level job settings](#recognized-keywords-in-top-level-scope),
[site-specific submissions settings](#recognized-keywords-in-machine-scope) (under *machine*), and
[what codes to run and how](#recognized-keywords-in-code-scope) (under *run*).
The recongized keywords in each of the scopes are itemized below. More example usage will follow.


## Recognized keywords in top-level scope

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

## Recognized keywords in machine scope

- *name*: name
- *charge*: account to charge node-hours
- *queue*: specify queue partition when multiple are available
- *job_setup*: shell script to run on service node before the main executables launch, as if in the scheduler submission file – setup modules, etc.
- *submit_setup*: shell script to run on login node, at composition time, i.e. before submission
- *scheduler_args*: additional settings to give to MPI launcher

## Recognized keywords in code scope

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
