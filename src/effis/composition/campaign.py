import os
import copy
import getpass
import shutil
import re
import json
import stat
import multiprocessing

import codar.cheetah
import codar.savanna

import effis.composition
from effis.composition.log import CompositionLogger
from effis.composition.application import LoginNodeApplication


def InputCopy(setup):
    
    for item in setup.Input.list:
        outpath = setup.Directory
        if item.outpath is not None:
            outpath = os.path.join(outpath, item.outpath)
            if not os.path.exists(outpath):
                os.makedirs(outpath)
        if item.rename is not None:
            outpath = os.path.join(outpath, item.rename)
        else:
            outpath = os.path.join(outpath, os.path.basename(item.inpath))
        
        if item.link:
            os.symlink(os.path.abspath(item.inpath), outpath)
        else:
            if os.path.isdir(item.inpath):
                shutil.copytree(item.inpath, outpath)
            else:
                shutil.copy(item.inpath, outpath)


def UpdateJSON(jsonfile, newnodes):
    with open(jsonfile, 'r') as infile:
        fob = json.load(infile)
    if type(fob) is dict:
        fob["total_nodes"] = newnodes
    elif type(fob) is list:
        fob[0]["total_nodes"] = newnodes
    with open(jsonfile, 'w', encoding='utf-8') as outfile:
        json.dump(fob, outfile, ensure_ascii=False, indent=4)


def FixCheetah():
    fixfile = os.path.join(os.path.dirname(codar.__file__), "savanna", "pipeline.py" )
    with open(fixfile) as infile:
        txt = infile.read()
    fixstr = 'self._get_path'
    if txt.find(fixstr) != -1:
        pattern = re.compile(fixstr, re.MULTILINE)
        txt = pattern.sub('get_path', txt)
        with open(fixfile, "w") as outfile:
            outfile.write(txt)


class Campaign(codar.cheetah.Campaign):

    NodeInfoFilename = ".effis.nodeinfo.json"
    
    # Find the correct node type
    def GetNodeType(self, workflow):
        NodeName = "{0}Node".format(self.machine.capitalize())

        if workflow.Node is not None:
            self.NodeType = workflow.Node

        elif NodeName in codar.savanna.machines.__dict__:
            self.NodeType = codar.savanna.machines.__dict__[NodeName]()
            if self.machine.lower() == "perlmutter_gpu":
                workflow.SchedulerDirectives += "--constraint=gpu"
            elif self.machine.lower() == "perlmutter_cpu":
                workflow.SchedulerDirectives += "--constraint=cpu"

        elif self.machine.lower() in effis.composition.node.effisnodes:
            self.NodeType = effis.composition.node.effisnodes[self.machine.lower()]
            if self.machine.lower() == "perlmutter_gpu":
                workflow.SchedulerDirectives += "--constraint=gpu"
            elif self.machine.lower() == "perlmutter_cpu":
                workflow.SchedulerDirectives += "--constraint=cpu"

        elif self.machine.lower() == "perlmutter":
            args = ' '.join(workflow.SchedulerDirectives.arguments)
            pattern = re.compile(r"--constraint(=|\s*)(gpu|cpu)")
            match = pattern.search(args)
            if match is not None:
                self.machine = "{0}_{1}".format(self.machine.lower(), match.group(2))
                self.NodeType = effis.composition.node.effisnodes["{0}_thread".format(self.machine)]
            else:
                #CompositionLogger.RaiseError(ValueError, "Need a --constraint for gpu or cpu with perlmutter")

                group = "cpu"
                for app in workflow.Applications:
                    if ((app.GPUsPerRank is not None) and (app.GPUsPerRank > 0)) or ((app.RanksPerGPU is not None) and (app.RanksPerGPU > 0)):
                        group = "gpu"
                        workflow.SchedulerDirectives += "--constraint=gpu"
                        break
                self.machine = "{0}_{1}".format(self.machine.lower(), group)
                self.NodeType = effis.composition.node.effisnodes["{0}_thread".format(self.machine)]
                if group == "cpu":
                    workflow.SchedulerDirectives += "--constraint=cpu"
                    CompositionLogger.Warning(
                        "Did not specifically ask for CPU or GPU partition. " +
                        "Using CPU since no GPUs were requested with Application settings."
                    )

        elif self.machine == "local":
            cpu_count = multiprocessing.cpu_count()
            self.NodeType = effis.composition.Node(cores=cpu_count, gpus=0)
            CompositionLogger.Warning("Cannot find known Node. Using 'local' detection: cores={0} (without GPU detection)".format(cpu_count))

        else:
            CompositionLogger.RaiseError(ValueError, "Could not find a MachineNode for {0}. Please set an effis.composition.Node".format(self.machine))



    
    # Map the .cpu, .gpu lists for the nodes
    def SetNodeLayout(self, workflow):
        
        self.GetNodeType(workflow)
        self.node_layout = {self.machine: []}
        
        self.LoginIndex = None
        index = 0
        ShareIndex = {}
        AppIndex = {}

        for app in workflow.Applications:

            if (app.ShareKey is not None) and (app.ShareKey not in ShareIndex):
                ShareIndex[app.ShareKey] = index
                AppIndex[app.Name] = index
                self.node_layout[self.machine] += [copy.deepcopy(self.NodeType)]
                index += 1
            elif (app.ShareKey is not None):
                AppIndex[app.Name] = ShareIndex[app.ShareKey]
            elif type(app) is LoginNodeApplication:
                if self.LoginIndex is None:
                    self.node_layout[self.machine] += [copy.deepcopy(self.NodeType)]
                    self.LoginIndex = index
                    index += 1
                app.CoresPerRank = 1
                AppIndex[app.Name] = self.LoginIndex
                """
                self.LoginNode += [index]
                AppIndex[app.Name] = index
                self.node_layout[self.machine] += [copy.deepcopy(self.NodeType)]
                if app.CoresPerRank is None:
                    app.CoresPerRank = len(self.node_layout[self.machine][index].cpu) // app.RanksPerNode
                index += 1
                """
            else:
                AppIndex[app.Name] = index
                self.node_layout[self.machine] += [copy.deepcopy(self.NodeType)]
                if app.CoresPerRank is None:
                    app.CoresPerRank = len(self.node_layout[self.machine][index].cpu) // app.RanksPerNode
                index += 1
                
            if app.RanksPerNode * app.CoresPerRank > len(self.NodeType.cpu):
                CompositionLogger.RaiseError(ValueError, "{0}: RanksPerNode={1}, CoresPerRank={2} doesn't make sense for Node with {3} cores".format(app.Name, app.RanksPerNode, app.CoresPerRank, len(self.NodeType.cpu)))
        

        for app in workflow.Applications:

            """
            if type(app) is LoginNodeApplication:
                continue
            """

            # Do the node layout
            index = AppIndex[app.Name]
            cstart, gstart = self.FindNext(index)
            
            for i in range(app.RanksPerNode):
                for j in range(app.CoresPerRank):
                    ind = cstart + i*app.CoresPerRank + j
                    if ind >= len(self.node_layout[self.machine][index].cpu):
                        CompositionLogger.RaiseError(ValueError, "{0} trying to set CPU {1} when there are only {2} for the Node".format(app.Name, ind+1, len(self.node_layout[self.machine][index].cpu)))
                    self.node_layout[self.machine][index].cpu[ind] = "{0}:{1}".format(app.Name, i)

            gpunum, ranknum = app.GPUvsRank()

            if (gpunum is not None) and (ranknum is not None):
                gpugroups = app.RanksPerNode // ranknum
                for i in range(gpugroups):
                    for j in range(gpunum):
                        ind = gstart + j + i*gpunum
                        if ind >= len(self.node_layout[self.machine][index].gpu):
                            CompositionLogger.RaiseError(ValueError, "{0} trying to set GPU {1} when there are only {2} for the Node".format(app.Name, ind+1, len(self.node_layout[self.machine][index].gpu)))
                        self.node_layout[self.machine][index].gpu[ind] = []
                        for k in range(ranknum):
                            self.node_layout[self.machine][index].gpu[ind] += ["{0}:{1}".format(app.Name, k + i*ranknum)]
                            
        # Debug output for the process mapping
        self.DebugProcessMapping()
        
    
    # Debug output for the process mapping
    def DebugProcessMapping(self):
        for i in range(len(self.node_layout[self.machine])):
            count = 0
            out = []
            for j in range(len(self.node_layout[self.machine][i].cpu)):
                if self.node_layout[self.machine][i].cpu[j] == None:
                    out += ["{0}-{1}: {2}".format(j-count+1, j, self.node_layout[self.machine][i].cpu[j-1])]
                    break
                if (j > 0) and (self.node_layout[self.machine][i].cpu[j] != self.node_layout[self.machine][i].cpu[j-1]):
                    out += ["{0}-{1}: {2}".format(j-count+1, j, self.node_layout[self.machine][i].cpu[j-1])]
                    count = 0
                elif j == len(self.node_layout[self.machine][i].cpu) - 1:
                    out += ["{0}-{1}: {2}".format(j-count, j+1, self.node_layout[self.machine][i].cpu[j])]
                count += 1

            if i == self.LoginIndex:
                CompositionLogger.Debug("Login node (no MPI): {0}".format(', '.join(out)))
            else:
                CompositionLogger.Debug("Compute Node {0} cpus --> {1}".format(i, ', '.join(out)))
                CompositionLogger.Debug("Compute Node {0} gpus --> {1}".format(i, self.node_layout[self.machine][i].gpu))
            
    
    def SchedulerSet(self, wcomp, cname):
        if wcomp is not None:
            self.scheduler_options[self.machine][cname] = wcomp

    
    # Return where CPU, GPU have not yet been filled for a node
    def FindNext(self, index):
        NodeLayout = self.node_layout[self.machine][index]
        
        for i, cpu in enumerate(NodeLayout.cpu):
            if cpu == None:
                break

        j = None
        for j, gpu in enumerate(NodeLayout.gpu):
            if gpu == None:
                break

        return i, j
        
    
    def __init__(self, workflow):
        
        self.output_dir = os.path.join(workflow.WorkflowDirectory)  # Top level directory everything writes under
        self.name = workflow.Name                                   # This doesn't affect any directory names; jobname = codar.cheetah.$name-$sweepgroupname
        self.machine = workflow.Machine           # machine itself is not a Cheetah attribute

        # Make sure each Application has a name, and 0th level process mapping sanity
        for app in workflow.Applications:
            if app.Name is None:
                app.Name = os.path.basename(app.Filepath)
            app.CheckSensible()  # Basic checks against Rank settings that don't make sense


        # Find the correct node type; Map the .cpu, .gpu lists for the nodes
        self.SetNodeLayout(workflow)

        # Local imples mpiexec and doesn't support much; force it back to the Cheetah simple thing
        if self.machine == "local":
            self.node_layout[self.machine] = []
            for app in workflow.Applications:
                self.node_layout[self.machine] += [{app.Name: app.RanksPerNode}]

        # Set properties of the cheetah scheduler
        self.scheduler_options = {self.machine: {}}
        self.SchedulerSet(workflow.Queue, 'queue')
        self.SchedulerSet(workflow.Charge, 'project')
        self.SchedulerSet(workflow.Reservation, 'reservation')
        if len(workflow.SchedulerDirectives.arguments) > 0:
            self.SchedulerSet(' '.join(workflow.SchedulerDirectives.arguments), 'custom')  # Scheduler Directives, could add --constraint in SetNodeLayout
        self.supported_machines = [self.machine]  # EFFIS only uses one machine at a time, whereas Cheetah could take multiple
            
        
        # This is Cheeta's basic object for the Applications running. Each can be associated with sweep entites
        self.codes = []
        rc_dependency = {}

        # Keep track of login node apps (to fix Cheetah's node number)
        LoginApps = 0
        ExtraNodes = 0

        for app in workflow.Applications:
            code = {}
            code['exe'] = app.Filepath
            code['env'] = None
            if app.SetupFile is not None:
                code['env_file'] = app.SetupFile

            # Check if there are any login node application (e.g. for launching stuff internally)
            if type(app) is LoginNodeApplication:
                code['runner_override'] = True
                LoginApps += 1
                ExtraNodes += app.UseNodes

            self.codes += [(app.Name, code)]

            if app.DependsOn is not None:
                rc_dependency[app.Name] = app.DependsOn


        # Set the things Cheetah considers sweep entities
        sweepargs = []      
        for app in workflow.Applications:
            mpi = {}
            sweepargs += [codar.cheetah.parameters.ParamRunner(app.Name, "nprocs", [app.Ranks])]
            for i, arg in enumerate(app.CommandLineArguments.arguments):
                sweepargs += [codar.cheetah.parameters.ParamCmdLineArg(app.Name, "arg{0}".format(i+1), i+1, [arg])]
            for i, arg in enumerate(app.MPIRunnerArguments.arguments):
                mpi[arg] = ""
            if len(mpi) > 0:
                sweepargs += [codar.cheetah.parameters.ParamSchedulerArgs(app.Name, [mpi])]
            for key in app.Environment:
                sweepargs += [codar.cheetah.parameters.ParamEnvVar(app.Name, 'env-{0}'.format(key),  key, [app.Environment[key]])]

        # A couple other job properties
        walltime = workflow.Walltime.seconds + 3600*24*workflow.Walltime.days
        launchmode = "default"
        if workflow.MPMD:
            launchmode = "MPMD"

        sweep = codar.cheetah.parameters.Sweep(sweepargs, node_layout=self.node_layout, rc_dependency=rc_dependency)  # A job can have multiple cheetah sweeps; Each SweepGroup is a job
        sweepgroup = codar.cheetah.parameters.SweepGroup(workflow.SweepGroupLabel, walltime=walltime, parameter_groups=[sweep], component_subdirs=workflow.Subdirs, launch_mode=launchmode)
        self.sweeps = [sweepgroup]

        # Job level setup script
        if workflow.SetupFile is not None:
            self.app_config_scripts = {self.machine: os.path.realpath(workflow.SetupFile)}

        """
        if self.config['machine']['submit_setup'] is not None:
            self.run_dir_setup_script = os.path.realpath(self.config['machine']['submit_setup'])
        """

        FixCheetah()
        workflow.__dict__["post_script"] = os.path.join(os.path.abspath(workflow.WorkflowDirectory), "post.sh")
        self.run_post_process_script = workflow.post_script
        if not os.path.exists(workflow.WorkflowDirectory):
            os.makedirs(workflow.WorkflowDirectory)
        with open(self.run_post_process_script, "w") as postfile:
            postfile.write("#!/bin/bash\n")
            postfile.write('echo "Running post script"\n')
        os.chmod(
            self.run_post_process_script,
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IWUSR |
            stat.S_IRGRP | stat.S_IXGRP |
            stat.S_IROTH | stat.S_IXOTH
            )

        # Second argument is appdir (something like place executables are)
        super(Campaign, self).__init__(self.machine, "./")
        self.make_experiment_run_dir(self.output_dir)

        # Set attributes so the user can get the run directories
        workflow.__dict__['Directory'] = os.path.abspath(os.path.join(self.output_dir, getpass.getuser(), workflow.SweepGroupLabel, workflow.IterationLabel))
        for app in workflow.Applications:
            app.__dict__['Directory'] = workflow.Directory
            if workflow.Subdirs:
                app.__dict__['Directory'] = os.path.join(app.Directory, app.Name)

        # Copy the input files
        InputCopy(workflow)
        for app in workflow.Applications:
            InputCopy(app)

        # Simplify job name
        jobname = "CODAR_CHEETAH_CAMPAIGN_NAME"
        updir = os.path.join(self.output_dir, getpass.getuser(), workflow.SweepGroupLabel)
        envfile = os.path.join(updir, "group-env.sh")
        with open(envfile, "r") as infile:
            txt = infile.read()
        pattern = re.compile(r'export \s*{0}="(.*)"\s*$'.format(jobname), re.MULTILINE)
        txt = pattern.sub('export {0}="{1}"'.format(jobname, workflow.Name), txt)

        # Fix job size if using login node apps
        #if LoginApps > 0:
        if ExtraNodes > 1:
            nodesname = "CODAR_CHEETAH_GROUP_NODES"
            pattern = re.compile(r'export \s*{0}="(.*)"\s*$'.format(nodesname), re.MULTILINE)
            match = pattern.search(txt)
            nodes = int(match.group(1))

            #newnodes = nodes - LoginApps + ExtraNodes
            #newnodes = max(nodes - 1 + ExtraNodes, nodes)
            newnodes = nodes - 1 + ExtraNodes

            print("Found {0} nodes in cheetah file. Updating the value to {1}".format(nodes, newnodes))
            txt = pattern.sub('export {0}="{1}"'.format(nodesname, newnodes), txt)

            UpdateJSON(os.path.join(workflow.Directory, 'codar.cheetah.fob.json'), newnodes)
            UpdateJSON(os.path.join(updir, "fobs.json"), newnodes)

        # Write the updated file
        with open(envfile, "w") as outfile:
            outfile.write(txt)


        # t3d-01/esuchyta/EFFIS/submit.sh
        #--partition=$CODAR_CHEETAH_SCHEDULER_QUEUE \
        subfile = os.path.join(updir, "submit.sh")
        with open(subfile, "r") as infile:
            txt = infile.read()
        pattern = re.compile(r'--partition=\$CODAR_CHEETAH_SCHEDULER_QUEUE', re.MULTILINE)
        txt = pattern.sub('', txt)
        with open(subfile, "w") as outfile:
            outfile.write(txt)


        # Write number of nodes into a file for SimpleRunner
        for app in workflow.Applications:
            if type(app) is LoginNodeApplication:

                fob = {
                    'UseNodes': app.UseNodes,
                    'cpus': len(self.NodeType.cpu),
                    'gpus': len(self.NodeType.gpu),
                }
                
                jsonfile = os.path.join(workflow.Directory, app.Name, self.NodeInfoFilename)
                with open(jsonfile, 'w', encoding='utf-8') as outfile:
                    json.dump(fob, outfile, ensure_ascii=False, indent=4)

