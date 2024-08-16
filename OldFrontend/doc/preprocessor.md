# Using the Pre-processor

When EFFIS is installed, one of the scripts is `effis-cpp.py`. This is the EFFIS pre-processor,
a source-to-source engine that goes through the source files making the updates to the code needed for EFFIS.

Using `effis-cpp.py` looks like:

```
effis-cpp.py repo $REPO_TOP
```

* `$REPO_TOP`     The source directory to look through. (All subdirectories will be checked too.)

Options:

* `--suffix`      Each file that needs replacements will be written out as a new file, as ${base}${suffix}${ext}. The default is "-effis".
* `--tree-output` Ordinarily, updated source files write into the same directory as the corresponding source file. Setting `--tree-output` to
to a directory sends the output files to this directory, into subdirectories mimicking the original directory structure

Run `effis-cpp.py repo --help` for advanced options that usually aren't needed.
