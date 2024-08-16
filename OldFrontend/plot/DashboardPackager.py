#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function, unicode_literals

import yaml
import numpy as np
import subprocess
import os
import sys
import json
import re
import datetime

import adios2


def IndexJSON(config, indent=4):
    outdict = {}
    #for name in ['shot_name', 'run_name', 'username', 'machine_name', 'date']:
    for name in ['shot_name', 'run_name', 'username', 'machine_name']:
        outdict[name] = config['login'][name]
    outdict['date'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S+%f')
    outstr = json.dumps([outdict], indent=indent)

    httpdir = config['login']['http']
    indexfile = os.path.join(httpdir, 'index.json')
    rundir = os.path.join(httpdir, outdict['shot_name'], outdict['run_name'])
    timefile = os.path.join(rundir, "time.json")
    timedict = {"current": 0, "complete": False, "started": False}

    if not os.path.exists(rundir):
        os.makedirs(rundir)
        timestr = json.dumps(timedict, indent=indent)
        with open(timefile, 'w') as outfile:
            outfile.write(timestr)

    if os.path.exists(indexfile):
        with open(indexfile, mode='rb+') as infile:
            infile.seek(0,  2)
            infile.seek(-2, 1)
            infile.write(','.encode('utf-8'))
            outstr = outstr[1:-1] + '\n]'
            infile.write(outstr.encode('utf-8'))
    else:
        with open(indexfile, mode='w') as outfile:
            outfile.write(outstr)

    return timefile, timedict



if __name__ == "__main__":

    indent = 4
    yamlfile = "step-info.yaml"
    with open(yamlfile, 'r') as ystream:
        config = yaml.load(ystream, Loader=yaml.FullLoader)

    timefile, timedict = IndexJSON(config, indent=indent)
    del config['login']

    adios = adios2.ADIOS()

    setup = {}
    setup['done'] = 0
    setup['size'] = len(list(config.keys()))
    setup['LastStep'] = -1
    for name in config.keys():
        setup[name] = {}
        setup[name]['io'] = adios.DeclareIO(name)
        #setup[name]['io'].SetEngine('BP4')
        setup[name]['io'].SetParameter('OpenTimeoutSecs', '3600')

        setup[name]['opened'] = False
        setup[name]['LastStep'] = np.array([-1], dtype=np.int32)
        setup[name]['done'] = False


    while True:

        if setup['done'] == setup['size']:
            timedict['complete'] = True
            timestr = json.dumps(timedict, indent=indent)
            with open(timefile, 'w') as outfile:
                outfile.write(timestr)
            break

        for name in config.keys():

            if setup[name]['done']:
                continue

            if not setup[name]['opened']:
                # Need to have a filename here
                setup[name]['engine'] = setup[name]['io'].Open(config[name], adios2.Mode.Read)
                setup[name]['opened'] = True

            ReadStatus = setup[name]['engine'].BeginStep(adios2.StepMode.Read, 0.1)

            if ReadStatus == adios2.StepStatus.NotReady:
                continue
            elif ReadStatus != adios2.StepStatus.OK:
                print("Found last in ", name); sys.stdout.flush()
                setup[name]['done'] = True
                setup['done'] += 1
                setup[name]['engine'].Close()
                continue

            varid = setup[name]['io'].InquireVariable("Step")
            setup[name]['engine'].Get(varid, setup[name]['LastStep'])
            setup[name]['engine'].EndStep()


        check = 0
        minfound = None
        for name in config.keys():
            if (setup[name]['LastStep'][0] <= setup['LastStep']) and (not setup[name]['done']):
                break
            if (minfound is None) or (setup[name]['LastStep'][0] < minfound):
                minfound = setup[name]['LastStep'][0]
            check += 1


        if check == setup['size']:

            for i in range(setup['LastStep']+1, minfound+1):
                print("Done: ", i); sys.stdout.flush()

                vardict = []
                vardir = os.path.join(os.path.dirname(timefile), "{0}".format(i))
                varfile = os.path.join(vardir, "variables.json")
                if not os.path.exists(vardir):
                    os.makedirs(vardir)
                
                tarargs = []
                allfiles = []
                allgroups = []
                for name in config.keys():
                    topdir = os.path.dirname(config[name])

                    code, label = name.split('.', 1)
                    label = os.path.basename(config[name])[:-8]

                    middir = os.path.join(topdir, "{0}-images".format(label), str(i))
                    name = "{0}-{1}".format(code, name)
                    subdir = os.path.join(middir, name)
                    print(subdir)

                    #middir = os.path.join(topdir, "images", str(i))
                    #subdir = os.path.join(middir, name)

                    if os.path.exists(subdir):
                        files = os.listdir(subdir)
                        #tarargs += ["-C", subdir] + files
                        tarargs += ["-C", middir, name]

                        if "plots.json" in files:
                            with open(os.path.join(subdir, "plots.json")) as jfile:
                                vardict += json.loads(jfile.read())
                        else:
                            allfiles += files
                            for j in range(len(files)):
                                allgroups += [name]

                for filename, groupname in zip(allfiles, allgroups):
                    fname = os.path.basename(filename)
                    name, ext = os.path.splitext(fname)

                    # I should make this a double underscore or something
                    try:
                        yname, xname = name.split('_vs_')
                    except:
                        pattern = "([a-zA-Z0-9]*).*"
                        comp = re.compile(pattern)
                        match = comp.search(name)
                        yname = match.group(1)

                    vardict += [{'variable_name': yname, 'image_name': filename, 'group_name': groupname}]

                tarfile = os.path.join(vardir, "images.tar.gz".format(i))
                if len(tarargs) > 0:
                    subprocess.call(['tar', 'cfzh', tarfile] + tarargs)
                else:
                    if not os.path.exists("images"):
                        os.makedirs("images")
                    subprocess.call(['tar', 'cfz', tarfile, "images/"])

                timedict['current'] = i
                timedict['started'] = True
                timestr = json.dumps(timedict, indent=indent)
                with open(timefile, 'w') as outfile:
                    outfile.write(timestr)

                varstr = json.dumps(vardict, indent=indent)
                with open(varfile, 'w') as outfile:
                    outfile.write(varstr)

            setup['LastStep'] = minfound

