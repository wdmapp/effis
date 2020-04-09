#!/usr/bin/env python


# Let's keep everything tested with python 2 and python 3
from __future__ import absolute_import, division, print_function, unicode_literals


# Cheetah is from CODAR. It's the interface through which you use CODAR's Savanna, which composes workflows
import codar.cheetah as cheetah
from codar.savanna.machines import SummitNode


# Other imports
import argparse
import copy
import datetime
import getpass
import logging
import re
import os
import shutil
import subprocess
import sys
import getpass
import yaml

import collections
from collections import OrderedDict

import kittie_common


def dict_representer(dumper, data):
    return dumper.represent_dict(data.items())

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

class OrderedLoader(yaml.Loader):
    pass

class OrderedDumper(yaml.Dumper):
    pass


def KeepLinksCopy(inpath, outpath):
    if os.path.isdir(inpath):
        shutil.copytree(inpath, outpath, symlinks=True)
    else:
        shutil.copy(inpath, outpath, follow_symlinks=False)


class KittieJob(cheetah.Campaign):

    def _KeywordSetup(self):
        """
        The keywords.yaml file defines the keyword setup. Change the file change the names
        """

        filepath = os.path.realpath(__file__)
        dirname = os.path.dirname(os.path.dirname(filepath))
        keywordspath = os.path.join(dirname, "config", "keywords.yaml")

        with open(keywordspath, 'r') as ystream:
            config = yaml.load(ystream, Loader=self.OrderedLoader)

        self.keywords = {}
        for key in config.keys():
            self.keywords[key] = config[key]

        for name in ['args', 'options', 'path', 'filename', 'engine', 'params', 'processes', 'processes-per-node', 'node-share', 'share-nodes']:
            if name not in self.keywords.keys():
                self.keywords[name] = name


    def _SetIfNotFound(self, dictionary, keyword, value=None, level=logging.INFO):
        """
        Method to set a config variable to some default value if it doesn't appear in the user's input config file.
        We may want to log too, warn, or possible abort trying to set something up if it's not given.
        """

        kw = self.keywords[keyword]
        if kw  not in dictionary.keys():
            msg = "{0} keyword not found in configuration file.".format(kw)

            if level == logging.ERROR:
                msg = "{0} It is required. Exiting".format(msg)
                self.logger.error(msg)
                sys.exit(1)
                #raise ValueError(msg)

            elif level == logging.WARNING:
                output = self.logger.warning
            elif level == logging.INFO:
                output = self.logger.info

            msg = "{0} Setting it to {1}".format(msg, value)
            output(msg)
            dictionary[kw] = value


    def _BlankInit(self, names, dictionary, value):
        """
        Helper for empty iterables
        """

        for name in names:
            if name not in dictionary.keys():
                dictionary[name] = copy.copy(value)


    def _DefaultArgs(self):
        """
        There are a reasonable number of config params. It's a good idea to have some automated defaulting going on.
        """

        # Some things that'll be given to Cheetah
        self.cheetahdir = '.cheetah'
        self.groupname = "kittie-run"

        """
        # Even older name
        self.cheetahsub = os.path.join(getpass.getuser(), self.groupname, 'run-{0:03d}'.format(0))

        # Older dev version of name
        self.cheetahsub = os.path.join(getpass.getuser(), self.groupname, 'run-0.0'.format(0))
        """

        # node-layout branch version of the name
        self.cheetahsub = os.path.join(getpass.getuser(), self.groupname, 'run-0.iteration-0'.format(0))


        # Do something (possible warn or exit) if certain things aren't found
        self._SetIfNotFound(self.config, 'machine', level=logging.ERROR)
        self._SetIfNotFound(self.config['machine'], 'name', level=logging.ERROR)
        if self.config['machine']['name'] != 'local':
            self._SetIfNotFound(self.config, 'walltime', 1800, level=logging.WARNING)
        else:
            self._SetIfNotFound(self.config, 'walltime', 1800, level=logging.INFO)

        self._SetIfNotFound(self.config, 'rundir',  'kittie-run', level=logging.WARNING)
        self.config[self.keywords['rundir']] = os.path.realpath(self.config[self.keywords['rundir']])

        self._SetIfNotFound(self.config, 'use-dashboard', False, level=logging.INFO)
        self._SetIfNotFound(self.config, 'dashboard', {}, level=logging.INFO)
        self._SetIfNotFound(self.config, 'login-proc', {}, level=logging.INFO)

        self._SetIfNotFound(self.config, 'jobname', 'kittie-job', level=logging.INFO)
        self._SetIfNotFound(self.config, 'mpmd', False, level=logging.INFO)
        self._SetIfNotFound(self.config, 'share-nodes', [], level=logging.INFO)

        self._SetIfNotFound(self.config['machine'], 'job_setup', value=None, level=logging.INFO)
        self._SetIfNotFound(self.config['machine'], 'submit_setup', value=None, level=logging.INFO)
        self._SetIfNotFound(self.config['machine'], 'script', value=None, level=logging.INFO)

        self._SetIfNotFound(self.config['machine'], 'scheduler_args', value=None, level=logging.INFO)


        # Allow certain sets of keywords generally in different parts of the config file, and initialize then to be empty
        allscopes_list = [self.keywords['copy'], self.keywords['copycontents'], self.keywords['link']]
        allscopes_dict = [self.keywords['file-edit']]
        self._BlankInit(allscopes_dict, self.config, {})
        self._BlankInit(allscopes_list, self.config, [])

        self.codesetup = dict(self.config['run'])
        self.codenames = list(self.codesetup.keys())

        self.codescope_list = allscopes_list + [self.keywords['args']]

        #self.codescope_list = allscopes_list + ['args', 'options']
        #self.codescope_dict = allscopes_dict + ['groups']
        self.codescope_dict = allscopes_dict + [self.keywords['options']]
        for codename in self.codenames:
            self._BlankInit(self.codescope_dict, self.codesetup[codename], {})
            self._BlankInit(self.codescope_list, self.codesetup[codename], [])
            self._SetIfNotFound(self.codesetup[codename], 'scheduler_args', value=None, level=logging.INFO)
            self._SetIfNotFound(self.codesetup[codename], 'processes', value=1, level=logging.INFO)
            self._SetIfNotFound(self.codesetup[codename], 'processes-per-node', value=1, level=logging.INFO)


    def _Unmatched(self, match):
        unmatched_close = '^[^\{]*\}'
        usearch = re.compile(unmatched_close)
        un1 = usearch.search(match)
        unmatched_open = '\{[^\}]*$'
        usearch = re.compile(unmatched_open)
        un2 = usearch.search(match)

        matches = []
        if (un1 is not None) and (un2 is not None):
            matches.append(match[:un1.end()-1])
            matches.append(match[un2.start()+1:])
            return matches
        else:
            return [match]


    def _MakeReplacements(self, searchstr=None, main=None, include=False):
        """
        Look for ${} things to be replaced in the user's input config file, and replace them with the values defined elsewhere in the file.
        """

        # The alternate method wan't fully working yet
        # I discontinued the [] instead of . dictionary indexing b/c it became hard to read
        #_self.AlternateReplacementChecking()


        # Did we call the function the first time, or are we doing it recursively?
        if searchstr is None:
            searchstr = yaml.dump(self.config, default_flow_style=False, Dumper=self.OrderedDumper)
            main = True
        else:
            if main is None:
                main = False


        pattern = '(?<!\$)\$\{(.*)\}'
        search = re.compile(pattern)
        results = search.findall(searchstr)

        for match in results:
            if main:
                self.config = yaml.load(searchstr.replace('$${', '${'), Loader=self.OrderedLoader)
            origmatches = self._Unmatched(match)

            for i, origmatch in enumerate(origmatches):
                match = origmatch

                # This assumes that lists always end the entries. That's probably OK, at least for now
                mpattern = "(.*)\[(\d*)\]$"
                msearch = re.compile(mpattern)
                index = []

                # Iteratively lookis for lists ending the objects
                while True:
                    subresults = msearch.findall(match)
                    if len(subresults) == 0:
                        break

                    index.insert(0, int(subresults[0][1]))
                    match = subresults[0][0]

                # The name location itself by be defined in terms of other things, so call the method on that too to resolve it
                match = self._MakeReplacements(match, include=include)
                keys = match.split(".")
                value = self.config

                try:
                    # Set the located value in our config text that weve been looking through to replace to the old value
                    for key in keys:
                        value = value[key]
                    for i in index:
                        value = value[i]

                    if len(origmatches) > 1:
                        omatch = match
                    else:
                        omatch = origmatch
                    for m in ['.', '[', '[', '$']:
                        omatch = omatch.replace(m, '\{0}'.format(m))
                    subpattern = "{1}{0}{2}".format(omatch, '\$\{', '\}')

                    subsearch = re.compile(subpattern)
                    if type(value) is collections.OrderedDict:
                        searchstr = subsearch.sub(str(dict(value)), searchstr, count=1)
                    else:
                        searchstr = subsearch.sub(str(value), searchstr, count=1)
                except(KeyError):
                    pass


        # Propogate the changes back into the config dictionary
        if main:
            searchstr = searchstr.replace('$${', '${')
            self.config = yaml.load(searchstr, Loader=self.OrderedLoader)
            results = search.findall(searchstr)
            if (len(results) > 0) and (not include):
                match = self._MakeReplacements(include=include)
            else:
                return searchstr
        else:
            return searchstr


    def _Copy(self, copydict, outdir):
        """
        Save files into the job area
        """

        # Do the user's requested links and copies
        for name in copydict[self.keywords['link']]:
            if type(name) == list:
                newpath = os.path.join(outdir, name[1])
                os.symlink(name[0], newpath)
            else:
                newpath = os.path.join(outdir, os.path.basename(name))
                os.symlink(name, newpath)

        for name in copydict[self.keywords['copycontents']]:
            if os.path.isdir(name):
                for subname in os.listdir(name):
                    subpath = os.path.join(name, subname)
                    newpath = os.path.join(outdir, os.path.basename(subname))
                    KeepLinksCopy(subpath, newpath)
            else:
                newpath = os.path.join(outdir, os.path.basename(name))
                shutil.copy(name, newpath, follow_symlinks=False)

        for name in copydict[self.keywords['copy']]:
            if type(name) == list:
                newpath = os.path.join(outdir, os.path.basename(name[1]))
                KeepLinksCopy(name[0], newpath)
            else:
                newpath = os.path.join(outdir, os.path.basename(name))
                KeepLinksCopy(name, newpath)


        # Do the user's requested file editing
        edits = copydict[self.keywords['file-edit']]
        for filename in edits.keys():
            filepath = os.path.join(outdir, filename)
            if not os.path.exists(filepath):
                self.logger.warning("{0} does not exist. Ignorning request to edit the file.".format(filepath))
                continue
            with open(filepath) as instream:
                txt = instream.read()

            # Handle search and replacement as Python regular expressions
            replacements = edits[filename]
            for replacement in replacements:
                search = re.compile(replacement[0], re.MULTILINE)
                txt = search.sub(replacement[1], txt)

            # Save a backup file of what the old file looked like
            bdir = os.path.join(os.path.dirname(filepath), ".bak")
            if not os.path.exists(bdir):
                os.makedirs(bdir)

            # Writ the updated file
            shutil.copy(filepath, os.path.join(bdir, os.path.basename(filepath)))
            with open(filepath, 'w') as outstream:
                outstream.write(txt)


    def _DoCommands(self, path, dictionary):
        keyword = self.keywords['pre-sub-cmds']
        if keyword in dictionary.keys():
            os.chdir(path)
            for cmd in dictionary[keyword]:
                args = cmd.split()
                subprocess.call(args)


    ###################################################################################################################################################
    ### Below here are the methods that the __init__() directly calls. The distinction isn't super important, but useful for categorizing thef file
    ###################################################################################################################################################

    def LoggerSetup(self):
        """
        Kittie automatially keeps track of a logfile (named by the current system time).
        If there is an error while this script is running, it will save the log to kittie-failure-logs/
        In the case there the script completes, it copies the log into the user's output directory
        Anything warning level or more severe will print to the screen too.
        I may make the different verbosities configurable.
        """

        # Python's loggers belong to a namespace
        self.logger = logging.getLogger(__name__)

        # Make sure the top level part of the logger handles all messages. Different handlers can set different verbosities
        self.logger.setLevel(logging.DEBUG)

        # Set the output formatting style
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        time = datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')

        # Where to write the log file
        self.logfile = os.path.join(os.path.realpath("kittie-failure-logs"), "{0}.log".format(time))
        dirname = os.path.dirname(self.logfile)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        # File handler
        self.filehandler = logging.FileHandler(self.logfile)
        self.filehandler.setLevel(logging.INFO)
        self.filehandler.setFormatter(formatter)

        # Stream = console (terminal) output
        self.streamhandler = logging.StreamHandler()
        self.streamhandler.setLevel(logging.WARNING)
        self.streamhandler.setFormatter(formatter)

        self.logger.addHandler(self.filehandler)
        self.logger.addHandler(self.streamhandler)


    def YAMLSetup(self):
        self.OrderedLoader = OrderedLoader
        self.OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, dict_constructor)
        self.OrderedDumper = OrderedDumper
        self.OrderedDumper.add_representer(collections.OrderedDict, dict_representer)


    def GetAppName(self, setupfile):
        with open(setupfile, 'r') as infile:
            nmltxt = infile.read()
        pattern = "^appname\s*=\s*(.*)$"
        search = re.compile(pattern, re.MULTILINE)
        results = search.search(nmltxt)

        if results is None:
            raise ValueError("Did not find appname in {0}".format(setupfile))
        name = results.group(1).strip("'").strip('"')
        return name


    def init(self, yamlfile):
        """
        init() is what does the Cheetah-related setup.
        It doesn't require the user to write a Cheetah class file. It reads the Kittie config file, and then figures out how to subclass Cheetah.
        """

        self.YAMLSetup()

        # Read in the config file
        with open(yamlfile, 'r') as ystream:
            self.config = yaml.load(ystream, Loader=self.OrderedLoader)


        # Kittie allows the user to set their own names for the fields in the config file if she wants.
        self._KeywordSetup()


        # Include other YAML files
        self._SetIfNotFound(self.config, 'include', [], level=logging.INFO)
        if len(self.config[self.keywords['include']]) > 0:
            try:
                self._MakeReplacements(include=True)
            except(KeyError):
                pass
        for filename in self.config[self.keywords['include']]:
            with open(filename, 'r') as ystream:
                self.config.update(yaml.load(ystream), Loader=self.OrderedLoader)


        # Make value replacements -- this when the user does things like processes-per-node: ${run.xgc.processes}
        self._MakeReplacements()


        # Set defaults if they're not found in the config file
        self._DefaultArgs()


        # Global Cheetah keywords
        self.output_dir = os.path.join(self.config[self.keywords['rundir']], self.cheetahdir)
        self.name = self.config[self.keywords['jobname']]


        # These are my own things, not Cheetah things per se, but are convenient to work with the Cheetah output
        self.mainpath = os.path.realpath(os.path.join(self.output_dir, self.cheetahsub))
        self.machine = self.config['machine']['name']
        machinekeys = self.config['machine'].keys()
        sweepargs = []


        # Machine-based Cheetah options
        self.supported_machines = [self.machine]
        self.node_layout = {self.machine: []}
        self.scheduler_options = {self.machine: {}}
        if 'charge' in machinekeys:
            self.scheduler_options[self.machine]['project'] = self.config['machine']['charge']
        if 'queue' in machinekeys:
            self.scheduler_options[self.machine]['queue'] = self.config['machine']['queue']


        # Cheetah options that Setup the codes that will lanuch
        self.codes = []

        if self.config[self.keywords['mpmd']]:
            self.launchmode = 'MPMD'
            subdirs = False
        else:
            self.launchmode = 'default'
            subdirs = True

        if self.config['machine'][self.keywords['script']] is not None:
            self.launchmode = 'default'
            subdirs = False

        
        self.stepinfo = {}
        lname = self.keywords['login-proc']
        uselogin = False

        # Insert ADIOS-based names Scott wants
        for k, codename in enumerate(self.codenames):
            thisdir = os.path.dirname(os.path.realpath(__file__))
            updir = os.path.dirname(thisdir)

            if (codename == "plot-triangular"):
                self.codesetup[codename][self.keywords['path']] = os.path.join(updir, "plot", "plotter-2d-triangular.py")

                if ('use' in self.config[self.keywords['dashboard']]) and (self.config[self.keywords['dashboard']]['use']):
                    self.codesetup[codename][self.keywords['options']]['use-dashboard'] = 'on'
                    if not uselogin:
                        self.config[lname] = self.config[self.keywords['dashboard']]
                        uselogin = True

            if (codename == "plot-colormap"):
                self.codesetup[codename][self.keywords['path']] = os.path.join(updir, "plot", "plotter-2d.py")
                if "only" in self.codesetup[codename]:
                    self.codesetup[codename][self.keywords['args']] += [self.codesetup[codename]["only"]]
                    self.codesetup[codename][self.keywords['options']]["only"] = self.codesetup[codename]["only"]
                elif "match-dimensions" in self.codesetup[codename]:
                    self.codesetup[codename][self.keywords['args']] += [self.codesetup[codename]["match-dimensions"]]
                if "data" in self.codesetup[codename]:
                    self.codesetup[codename]['.plotter'] = {'plots': self.codesetup[codename]["data"]}

                if 'colortype' in self.codesetup[codename]:
                    self.codesetup[codename][self.keywords['options']]["colormap"] = self.codesetup[codename]["colortype"]
                if 'viewtype' in self.codesetup[codename]:
                    self.codesetup[codename][self.keywords['options']]["type"] = self.codesetup[codename]["viewtype"]

                if ('use' in self.config[self.keywords['dashboard']]) and (self.config[self.keywords['dashboard']]['use']):
                    self.codesetup[codename][self.keywords['options']]['use-dashboard'] = 'on'
                    if not uselogin:
                        self.config[lname] = self.config[self.keywords['dashboard']]
                        uselogin = True

            if (codename == "plot-1D"):
                self.codesetup[codename][self.keywords['path']] = os.path.join(updir, "plot", "plotter-1d.py")
                self.codesetup[codename][self.keywords['options']]['output'] = 'matplot'
                if "x" in self.codesetup[codename]:
                    self.codesetup[codename][self.keywords['args']] += [self.codesetup[codename]['x']]
                if "y" in self.codesetup[codename]:
                    self.codesetup[codename][self.keywords['options']]['y'] = self.codesetup[codename]['y']
                if "output" in self.codesetup[codename]:
                    self.codesetup[codename][self.keywords['options']]['out'] = self.codesetup[codename]['output']
                if "data" in self.codesetup[codename]:
                    self.codesetup[codename]['.plotter'] = {'plots': self.codesetup[codename]["data"]}

                if ('use' in self.config[self.keywords['dashboard']]) and (self.config[self.keywords['dashboard']]['use']):
                    self.codesetup[codename][self.keywords['options']]['use-dashboard'] = 'on'
                    if not uselogin:
                        self.config[lname] = self.config[self.keywords['dashboard']]
                        uselogin = True

            if '.plotter' in self.codesetup[codename]:
                if 'data' in self.codesetup[codename]:
                    self.codesetup[codename]['.open-plotter'] = {'reads': self.codesetup[codename]["data"]}
                else:
                    self.codesetup[codename]['.open-plotter'] = {'reads': self.codesetup[codename]['.plotter']["plots"]}


        for codename in self.codenames:
            StepGroup = codename + "-step"
            groupname = "." + StepGroup
            if groupname not in self.codesetup[codename].keys():
                self.codesetup[codename][groupname] = {}
                self.codesetup[codename][groupname][self.keywords['engine']] = 'BP4'
                self.codesetup[codename][groupname][self.keywords['params']] = {}
                self.codesetup[codename][groupname][self.keywords['params']]["RendezvousReaderCount"] = 0
                self.codesetup[codename][groupname][self.keywords['params']]["QueueLimit"] = 1
                self.codesetup[codename][groupname][self.keywords['params']]["QueueFullPolicy"] = "Discard"


        self.timingdir = os.path.join(self.config[self.keywords['rundir']], 'effis-timing')
        for k, codename in enumerate(self.codenames):
            self.codesetup[codename]['groups'] = {}
            for key in self.codesetup[codename]:
                if key.startswith('.'):
                    name = key[1:]
                    entry = self.codesetup[codename][key]
                    self.codesetup[codename]['groups'][name] = self.codesetup[codename][key]
                    self.codesetup[codename]['groups'][name]['AddStep'] = False
                    self.codesetup[codename]['groups'][name]['timingdir'] = self.timingdir


        # Insert ADIOS-based names Scott wants
        for k, codename in enumerate(self.codenames):
            for key in self.codesetup[codename]['groups']:
                entry = self.codesetup[codename]['groups'][key]

                if self.keywords['filename'] in entry:
                    fname = entry[self.keywords['filename']]
                    if not fname.startswith('/'):
                        if self.launchmode != "MPMD":
                            fname = os.path.join(self.mainpath, codename, fname)
                        else:
                            fname = os.path.join(self.mainpath, fname)
                    self.codesetup[codename]['groups'][key]['filename'] = fname

                if self.keywords['engine'] in entry:
                    self.codesetup[codename]['groups'][key]['engine'] = entry[self.keywords['engine']]
                if self.keywords['params'] in entry:
                    self.codesetup[codename]['groups'][key]['params'] = entry[self.keywords['params']]


        # See if we're linking anything from other groups
        for k, codename in enumerate(self.codenames):

            for key in self.codesetup[codename]['groups']:
                entry = self.codesetup[codename]['groups'][key]

                if 'plots' in entry:
                    if 'reads' not in entry:
                        entry['reads'] = entry['plots']
                    else:
                        entry['reads'] += entry['plots']

                    thisdir = os.path.dirname(os.path.realpath(__file__))
                    mfile = os.path.join(os.path.dirname(thisdir), "plot", "matplotlibrc")
                    if mfile not in self.codesetup[codename][self.keywords['copy']]:
                        self.codesetup[codename][self.keywords['copy']] += [mfile]

                if 'reads' in entry:
                    code, group = entry['reads'].split('.', 1)
                    other = self.codesetup[code]['groups'][group]

                    if ('filename' not in other) and (('fromcode' not in other) or (not other['fromcode'])):
                        raise ValueError("If you're going to read {0}.{1} you need to set it's filename when it writes".format(code, group))
                    elif 'filename' in other:
                        self.codesetup[codename]['groups'][key]['filename'] = self.codesetup[code]['groups'][group]['filename']

                    if self.launchmode != "MPMD":
                        self.codesetup[codename]['groups'][key]['stepfile'] = os.path.join(self.mainpath, code, code + '-step.bp')

                    #self.codesetup[codename]['groups'][key]['filename'] = self.codesetup[code]['groups'][group]['filename']
                    if 'engine' in other:
                        self.codesetup[codename]['groups'][key]['engine'] = self.codesetup[code]['groups'][group]['engine']
                    if 'params' in other:
                        self.codesetup[codename]['groups'][key]['params'] = self.codesetup[code]['groups'][group]['params']

                    self.codesetup[code]['groups'][group]['AddStep'] = True
                    #self.codesetup[codename]['groups'][key]['FromApp'] = code +


        if ('use' in self.config[lname]) and self.config[lname]['use']:
            uselogin = True
            self.codenames += [lname]
            self.codesetup[lname] = {}
            self.codesetup[lname][self.keywords['args']] = []
            self.codesetup[lname]['scheduler_args'] = None
            self.codesetup[lname][self.keywords['options']] = {}
            self.codesetup[lname][self.keywords['path']] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "plot", "login.py")
            self.codesetup[lname]['processes'] = 1
            self.codesetup[lname]['processes-per-node'] = 1
            #self.codesetup[lname]['cpus-per-process'] = 1
            self.codesetup[lname][self.keywords['copy']] = []
            self.codesetup[lname][self.keywords['copycontents']] = []
            self.codesetup[lname][self.keywords['link']] = []
            self.codesetup[lname][self.keywords['file-edit']] = {}
            self.codesetup[lname]['groups'] = {}

            self.stepinfo['login'] = {}
            for name in ['shot_name', 'run_name', 'http']:
                if name not in self.config[lname]:
                    msg = "{0} is required with {1} on. Exiting".format(msg, lname)
                    self.logger.error(msg)
                    sys.exit(1)
                self.stepinfo['login'][name] = self.config[lname][name]

            self.stepinfo['login']['username'] = getpass.getuser()
            self.stepinfo['login']['date'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S+%f')
            self.stepinfo['login']['machine_name'] = self.config['machine']['name']

            for k, codename in enumerate(self.codenames):
                for j, groupname in enumerate(self.codesetup[codename]['groups']):
                    if 'plots' in self.codesetup[codename]['groups'][groupname]:
                        cname, gname = self.codesetup[codename]['groups'][groupname]['plots'].split('.', 1)
                        name = "{0}-{1}-StepsDone.bp".format(codename, gname)
                        if self.launchmode != "MPMD":
                            name = os.path.join(self.mainpath, codename, name)
                        else:
                            name = os.path.join(self.mainpath, name)
                        self.stepinfo['{0}.{1}'.format(cname, gname)] = name


        if "monitors" in self.codenames:
            self.codesetup["monitors"][self.keywords['path']] = os.path.join(updir, "bin", "kittie_monitor.py")
            self.monitors = {}
            self.monitors["monitors"] = self.codesetup["monitors"]
            self.monitors['groups'] = {}
            for cname in self.codenames:
                self.monitors['groups'][cname] = self.codesetup[cname]['groups']


        SharedNodes = {}
        added = []

        for k, codename in enumerate(self.codenames):
            codedict = {}
            codedict['exe'] = self.codesetup[codename][self.keywords['path']]
            
            # Added in node-layout branch
            if codename in [lname, "monitors"]:
                codedict['runner_override'] = True

            self.codes.append((codename, codedict))
            self.codesetup[codename]['setup-file'] = os.path.join(os.path.dirname(self.codesetup[codename][self.keywords['path']]), ".kittie-setup.nml")


            # Set the number of processes
            sweepargs += [cheetah.parameters.ParamRunner(codename, "nprocs", [self.codesetup[codename]['processes']])]


            # Set the node layout -- namely, it's different on summit
            entry = self.codesetup[codename]
            ns = self.keywords['node-share']
            sn = self.keywords['share-nodes']
            cpp = 1
            if 'cpus-per-process' in entry:
                cpp = entry['cpus-per-process']

            if self.machine == 'summit':

                #if ns not in entry:
                if len(self.config[sn]) == 0:
                    self.node_layout[self.machine] += [SummitNode()]
                    added += [codename]
                    index = -1
                    CPUstart = 0

                else:
                    found = False
                    for group in self.config[sn]:
                        cname = group[0]
                        if (codename in group) and (cname in SharedNodes):
                            found = True
                            break
                    if found:
                        for i, name in enumerate(added):
                            if name == cname:
                                index = i
                                break
                        CPUstart = SharedNodes[cname]
                    else:
                        cname = codename
                        index = -1
                        added += [codename]
                        CPUstart = 0
                        self.node_layout[self.machine] += [SummitNode()]
                    SharedNodes[cname] = CPUstart + entry['processes-per-node'] * cpp


                    """
                    for cname in entry[ns]:
                        print("codename: {0},  cname: {1},  SharedNodes: {2}".format(codename, cname, SharedNodes))
                        if cname in SharedNodes:
                            found = True
                            break

                    if found:
                        for i, name in enumerate(added):
                            if name == cname:
                                index = i
                                break
                        CPUstart = SharedNodes[cname]

                    else:
                        cname = codename
                        index = -1
                        added += [codename]
                        CPUstart = 0
                        self.node_layout[self.machine] += [SummitNode()]

                    SharedNodes[cname] = CPUstart + entry['processes-per-node'] * cpp
                    """


                for i in range(entry['processes-per-node']):
                    for j in range(cpp):
                        self.node_layout[self.machine][index].cpu[CPUstart + i*cpp + j] = "{0}:{1}".format(codename, i)

                    # This isn't exactly right yet
                    if ('use-gpus' in entry) and entry['use-gpus']:
                        self.node_layout[self.machine][index].gpu[i] = ["{0}:{1}".format(codename, i)]

            else:
                self.node_layout[self.machine] += [{codename: entry['processes-per-node']}]


            # Set the command line arguments
            args = self.codesetup[codename][self.keywords['args']]
            for i, arg in enumerate(args):
                sweepargs += [cheetah.parameters.ParamCmdLineArg(codename, "arg{0}".format(i+1), i+1, [arg])]

            # Set the command line options
            options = dict(self.codesetup[codename][self.keywords['options']])
            for i, option in enumerate(options.keys()):
                sweepargs += [cheetah.parameters.ParamCmdLineOption(codename, "opt{0}".format(i), "--{0}".format(option), [options[option]])]


            if self.config['machine'][self.keywords['scheduler_args']] is not None:
                sweepargs += [cheetah.parameters.ParamSchedulerArgs(codename, [dict(self.config['machine'][self.keywords['scheduler_args']])])]

            if self.codesetup[codename][self.keywords['scheduler_args']] is not None:
                sweepargs += [cheetah.parameters.ParamSchedulerArgs(codename, [dict(self.codesetup[codename][self.keywords['scheduler_args']])])]


            exedir = os.path.dirname(self.codesetup[codename][self.keywords['path']])
            sweepenv1 = cheetah.parameters.ParamEnvVar(codename, 'setup-file-yaml', 'KITTIE_YAML_FILE', [os.path.join(exedir, ".kittie-setup.yaml")])
            sweepenv2 = cheetah.parameters.ParamEnvVar(codename, 'setup-file-nml',  'KITTIE_NML_FILE',  [os.path.join(exedir, ".kittie-setup.nml" )])
            sweepenv3 = cheetah.parameters.ParamEnvVar(codename, 'setup-file-num',  'KITTIE_NUM', ['{0}'.format(k)])
            sweepargs += [sweepenv1, sweepenv2, sweepenv3]


        if uselogin and ('env' in self.config[lname]):
            for varname in self.config[lname]['env'].keys():
                sweepenv = cheetah.parameters.ParamEnvVar(lname, lname + "-" + varname, varname, [self.config[lname]['env'][varname]])
                sweepargs += [sweepenv]

        if ('ADIOS-serial' in self.config) and ('monitors' in self.codenames):
            sweepenv = cheetah.parameters.ParamEnvVar('monitors', "monitors-ADIOS", "ADIOS", [self.config['ADIOS-serial']])
            sweepargs += [sweepenv]


        # A sweep encompasses is a set of parameters that can vary. In my case nothing is varying, and the only sweep paramter is a single number of processes
        sweep = cheetah.parameters.Sweep(sweepargs, node_layout=self.node_layout)

        # A sweepgroup runs a sweep by submiting a single job. There could be more than one sweepgroup, given by the sweeps list attribute, which would submit mutliple inpedent jobs.
        sweepgroup = cheetah.parameters.SweepGroup(self.groupname, walltime=self.config[self.keywords['walltime']], parameter_groups=[sweep], component_subdirs=subdirs, launch_mode=self.launchmode)
        self.sweeps = [sweepgroup]


        if self.config['machine']['job_setup'] is not None:
            self.app_config_scripts = {self.machine: os.path.realpath(self.config['machine']['job_setup'])}

        if self.config['machine']['submit_setup'] is not None:
            self.run_dir_setup_script = os.path.realpath(self.config['machine']['submit_setup'])


    def Copy(self):
        """
        Copy() handles what the user asked to copy and/or symbolically link.
        It also makes the file edits the user user asks for and then copyies them into the output area.
        """

        self._Copy(self.config, self.mainpath)

        for codename in self.codenames:
            if self.launchmode == "MPMD":
                codepath = os.path.join(self.mainpath)
            else:
                codepath = os.path.join(self.mainpath, codename)
            self._Copy(self.codesetup[codename], codepath)



    def PreSubmitCommands(self):
        """
        PreSubmitCommands issues the commands that user asks for in the config file.
        These happend while this Kittie job setup is happening -- not during the actual compute job.
        One might do things like make directories.
        """
        self._DoCommands(self.mainpath, self.config)
        for codename in self.config['run']:
            if self.launchmode == "MPMD":
                path = self.mainpath
            else:
                path = os.path.join(self.mainpath, codename)
            self._DoCommands(path, self.config['run'][codename])



    def Link(self):
        """
        Link() takes care of presenting the user with correct Cheetah directory and files according to where the user wanted the output.
        It doesn't present the user with everything there b/c an "orindary" user likely won't understand what it is all is and could get confused.
        Everything from cheetash is still there, just grouped into the .cheetah directory.
        Link() uses symbolic links but it has nothing to do with the `link` keyword in the Kittie config file.
        """

        os.chdir(self.mainpath)
        mainlist = os.listdir(self.mainpath)
        os.makedirs(self.timingdir)

        if self.launchmode == "MPMD":
            linksrc = os.path.join(self.cheetahdir, self.cheetahsub)
            linkpath = os.path.join(self.config[self.keywords['rundir']], "run")
            os.symlink(linksrc, linkpath)

        else:
            for name in mainlist:
                if name.startswith('codar.cheetah.') or name.startswith('.codar.cheetah.') or  (name == "tau.conf"):
                    continue
                linksrc = os.path.join(self.cheetahdir, self.cheetahsub, name)
                linkpath = os.path.join(self.config[self.keywords['rundir']], name)
                os.symlink(linksrc, linkpath)



    def MoveLog(self):
        """
        If we get here, we've successfully built a cheetah job. Move the Kittie log into the output directory
        """

        outlog = os.path.join(self.config[self.keywords['rundir']], "kittie-setup-{0}".format(os.path.basename(self.logfile)) )
        shutil.move(self.logfile, outlog)
        checkdir = os.path.dirname(self.logfile)
        remaining = os.listdir(checkdir)
        if len(remaining) == 0:
            shutil.rmtree(checkdir)


    def WriteGroupsFile(self):

        for k, codename in enumerate(self.codenames):
            if codename == "kittie-plotter":
                continue

            gstrs = []
            pstrs = []
            params = []
            values = []

            keys = self.codesetup[codename]['groups'].keys()
            names = ["ionames", "nnames = {0}".format(len(keys)) + "\n" + "timingdir = '{0}'".format(self.timingdir)]

            for i, key in enumerate(keys):
                entry = self.codesetup[codename]['groups'][key]
                gstr = "names({0}) = '{1}'".format(i+1, key)
                nparams = 0

                if entry['AddStep']:
                    gstr = "{0}{1}kittie_addstep({2}) = T".format(gstr, '\n', i+1)

                if (self.keywords['timed'] in entry) and (entry[self.keywords['timed']]):
                    gstr = "{0}{1}kittie_timed({2}) = T".format(gstr, '\n', i+1)
                else:
                    gstr = "{0}{1}kittie_timed({2}) = F".format(gstr, '\n', i+1)


                if 'filename' in entry:
                    gstr = "{0}{1}kittie_filenames({2}) = '{3}'".format(gstr, '\n', i+1, entry['filename'])


                if 'engine' in entry:
                    engine = entry['engine']
                    if type(engine) is str:
                        gstr = "{0}{1}engines({2}) = '{3}'".format(gstr, '\n', i+1, engine)

                if 'params' in entry:
                    engineparams = list(entry['params'].keys())
                    nparams = len(engineparams)
                    gstr = "{0}{1}nparams({2}) = {3}".format(gstr, '\n', i+1, nparams)

                    for j in range(nparams):
                        key = engineparams[j]
                        params += ["params({0}, {1}) = '{2}'".format(i+1, j+1, key)]
                       
                        if type(entry['params'][key]) == bool:
                            if entry['params'][key]:
                                values += ["values({0}, {1}) = 'On'".format(i+1, j+1)]
                            else:
                                values += ["values({0}, {1}) = 'Off'".format(i+1, j+1)]
                        else:
                            values += ["values({0}, {1}) = '{2}'".format(i+1, j+1, entry['params'][key])]

                if "plot" in entry:
                    gstr = "{0}{1}nplots({2}) = {3}".format(gstr, "\n", i+1, len(entry['plot']))
                    for j, name in enumerate(entry['plot']):
                        pstrs += ["plots({0}, {1}) = '{2}'".format(i+1, j+1, name)]

                gstrs += [gstr]

            names_list = ["ionames_list", '\n'.join(gstrs)]
            plots_list = ["plots_list", '\n'.join(pstrs)]
            params_list = ["params_list", '\n'.join(params+values)]
            outstr = kittie_common.Namelist(names, names_list, plots_list, params_list)
            kittie_common.NMLFile("kittie-groups", self.mainpath, outstr, codename=codename, appname=k, launchmode=self.launchmode)

            if self.launchmode == "default":
                outdir = os.path.join(self.mainpath, codename)
            else:
                outdir = self.mainpath
            self.codesetup[codename]['groups'][".timingdir"] = self.timingdir
            outstr = yaml.dump(self.codesetup[codename]['groups'], default_flow_style=False, Dumper=self.OrderedDumper)
            outname = os.path.join(outdir, ".kittie-groups-{0}.yaml".format(k))
            with open(outname, "w") as outfile:
                outfile.write(outstr)

        if "monitors" in self.codenames:
            codename = "monitors"
            if self.launchmode == "default":
                outdir = os.path.join(self.mainpath, codename)
            else:
                outdir = self.mainpath

            outname = os.path.join(outdir, "groups.yaml")
            outstr = yaml.dump(self.monitors['groups'], default_flow_style=False, Dumper=self.OrderedDumper)
            with open(outname, "w") as outfile:
                outfile.write(outstr)

            outname = os.path.join(outdir, "monitor-config.yaml")
            outstr = yaml.dump(self.monitors['monitors'], default_flow_style=False, Dumper=self.OrderedDumper)
            with open(outname, "w") as outfile:
                outfile.write(outstr)


    def WriteCodesFile(self):
        gstrs = []
        for i, code in enumerate(self.codenames):
            gstrs.append("codenames({0}) = '{1}'".format(i+1, code))
        gstrs = '\n'.join(gstrs)

        for i, codename in enumerate(self.codenames):
            if codename == "kittie-plotter":
                continue
            nstrs = "ncodes = {0}{1}codename = '{2}'".format(len(self.codenames), '\n', codename)
            nlist = ["codes", nstrs]
            glist = ["codes_list", gstrs]
            outstr = kittie_common.Namelist(nlist, glist)
            kittie_common.NMLFile("kittie-codenames", self.mainpath, outstr, codename=codename, appname=i, launchmode=self.launchmode)

            if self.launchmode == "default":
                outdir = os.path.join(self.mainpath, codename)
            else:
                outdir = self.mainpath
            outdict = {'n': len(self.codenames), 'codename': str(codename), 'codes': list(self.codenames)}
            outstr = yaml.dump(outdict, default_flow_style=False)
            outname = os.path.join(outdir, ".kittie-codenames-{0}.yaml".format(i))
            with open(outname, 'w') as outfile:
                outfile.write(outstr)


    def WriteStepsFile(self):
        if self.stepinfo != {}:
            if self.launchmode != "MPMD":
                outname = os.path.join(self.mainpath, self.keywords['login-proc'], "step-info.yaml")
            else:
                outname = os.path.join(self.mainpath, "step-info.yaml")
            outstr = yaml.dump(self.stepinfo, default_flow_style=False)
            with open(outname, "w") as outfile:
                outfile.write(outstr)


    def FromScript(self):
        if self.config['machine'][self.keywords['script']] is not None:
            with open(os.path.join(self.mainpath, ".kittie-script.sh"), 'w') as outfile:
                outfile.write('cd {0}\n'.format(self.mainpath))
                outfile.write('bsub {0}'.format(self.config['machine'][self.keywords['script']]))


    def CopyInput(self, yamlfile):
        outdir = os.path.join(self.config[self.keywords['rundir']], '.kittie-input')
        os.makedirs(outdir)

        for filename in self.config[self.keywords['include']]:
            shutil.copy(filename, os.path.join(outdir, os.path.basename(filename)))

        shutil.copy(yamlfile, os.path.join(outdir, os.path.basename(yamlfile)))

        for k, codename in enumerate(self.codenames):
            try:
                filename = self.codesetup[codename]['setup-file']
            except:
                filename = None

            if (filename is not None) and os.path.exists(filename):
                basename = ".{0}".format(codename) + os.path.basename(filename)
                shutil.copy(filename, os.path.join(outdir, basename))


    def __init__(self, yamlfile):
        YamlFile = os.path.realpath(yamlfile)
        self.LoggerSetup()
        self.init(yamlfile)
        super(KittieJob, self).__init__(self.machine, "")
        self.make_experiment_run_dir(self.output_dir)

        if self.config['machine'][self.keywords['script']] is not None:
            self.launchmode = 'MPMD'

        self.Copy()
        self.PreSubmitCommands()
        self.Link()

        self.WriteCodesFile()
        self.WriteGroupsFile()
        self.WriteStepsFile()
        """
        self.WritePlotsFile()
        """

        self.FromScript()
        self.CopyInput(YamlFile)
        self.MoveLog()


if __name__ == "__main__":
    """
    main() doesn't do much itself. Just parses the commnand line args and initialized a Kittie object
    """

    # I'll probably need more args eventually, but probably not many -- maybe and --overwrite
    parser = argparse.ArgumentParser()
    parser.add_argument("configfile", help="Path to Kittie configuration file", metavar="Config-file")
    args = parser.parse_args()

    kittiejob = KittieJob(args.configfile)

