#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function, unicode_literals
import subprocess
import argparse
import os
import sys
import contextlib


@contextlib.contextmanager
def chdir(newdir):
    curdir = os.getcwd()
    os.chdir(newdir)
    try:
        yield
    finally:
        os.chdir(curdir)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Directory to job to run")
    args = parser.parse_args()

    backupfile = os.path.join(args.directory, ".effis-input", "effis-backup.yaml")
    if os.path.exists(backupfile):
        thisdir = os.path.dirname(os.path.abspath(__file__))
        p = subprocess.Popen(["effis-globus.py", backupfile], shell=False, stderr=subprocess.PIPE)
       
        error = False
        for line in iter(p.stderr.readline, b''):
            if line.decode("utf-8").rstrip() == "STATUS=READY":
                break
            elif line.decode("utf-8").rstrip() != "":
                print(line.decode("utf-8"), file=sys.stderr, end="")
                error = True
        if error:
            sys.exit(1)

        p.stderr = sys.stderr
      
    submitdir = os.path.join(args.directory, ".cheetah", os.environ["USER"])
    with chdir(submitdir):
        subprocess.Popen(["./run-all.sh"], shell=False)
