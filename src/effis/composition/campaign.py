import os
import copy
import getpass
import shutil
import sys

import codar.cheetah
import codar.savanna
from effis.composition.log import CompositionLogger


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



class Campaign(codar.cheetah.Campaign):

    
    # Find the correct node type
    def GetNodeType(self, workflow):
        NodeName = "{0}Node".format(self.machine.capitalize())
        if workflow.Node is not None:
            NodeType = workflow.Node
        elif NodeName in codar.savanna.machines.__dict__:
            NodeType = codar.savanna.machines.__dict__[NodeName]()
        else:
            CompositionLogger.RaiseError(ValueError, "Could not find a MachineNode for {0}. Please set an effis.composition.Node".format(self.machine))
        return NodeType

    
    # Map the .cpu, .gpu lists for the nodes
    def SetNodeLayout(self, workflow):
        
        self.node_layout = {self.machine: []}
        NodeType = self.GetNodeType(workflow)
        
        index = 0
        ShareIndex = {}
        AppIndex = {}

        for app in workflow.Applications:

            if (app.ShareKey is not None) and (app.ShareKey not in ShareIndex):
                ShareIndex[app.ShareKey] = index
                AppIndex[app.Name] = index
                self.node_layout[self.machine] += [copy.deepcopy(NodeType)]
                index += 1
            elif (app.ShareKey is not None):
                AppIndex[app.Name] = ShareIndex[app.ShareKey]
            else:
                AppIndex[app.Name] = index
                self.node_layout[self.machine] += [copy.deepcopy(NodeType)]
                if app.CoresPerRank is None:
                    app.CoresPerRank = len(self.node_layout[self.machine][index].cpu) // app.RanksPerNode
                index += 1
                
            if app.RanksPerNode * app.CoresPerRank > len(NodeType.cpu):
                CompositionLogger.RaiseError(ValueError, "{0}: RanksPerNode={1}, CoresPerRank={2} doesn't make sense for Node with {3} cores".format(app.Name, app.RanksPerNode, app.CoresPerRank, len(NodeType.cpu)))
        

        for app in workflow.Applications:

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
            CompositionLogger.Debug("Node {0} cpus --> {1}".format(i, ', '.join(out)))
            CompositionLogger.Debug("Node {0} gpus --> {1}".format(i, self.node_layout[self.machine][i].gpu))
            
    
    def SchedulerSet(self, wcomp, cname):
        if wcomp is not None:
            self.scheduler_options[self.machine][cname] = wcomp

    
    # Return where CPU, GPU have not yet been filled for a node
    def FindNext(self, index):
        NodeLayout = self.node_layout[self.machine][index]
        for i, cpu in enumerate(NodeLayout.cpu):
            if cpu == None:
                break
        for j, gpu in enumerate(NodeLayout.gpu):
            if gpu == None:
                break
        return i, j
        
    
    def __init__(self, workflow):
        
        self.output_dir = os.path.join(workflow.WorkflowDirectory)  # Top level directory everything writes under
        self.name = workflow.Name                                   # This doesn't affect any directory names; jobname = codar.cheetah.$name-$sweepgroupname
        self.machine = workflow.Machine           # machine itself is not a Cheetah attribute
        self.supported_machines = [self.machine]  # EFFIS only uses one machine at a time, whereas Cheetah could take multiple

        # Set properties of the cheetah scheduler
        self.scheduler_options = {self.machine: {}}
        self.SchedulerSet(workflow.Queue, 'queue')
        self.SchedulerSet(workflow.Charge, 'project')
        self.SchedulerSet(workflow.Reservation, 'reservation')
        if len(workflow.SchedulerDirectives.arguments) > 0:
            self.SchedulerSet(' '.join(workflow.SchedulerDirectives.arguments), 'custom')  # Scheduler Directives

        # Make sure each Application has a name, and 0th level process mapping sanity
        for app in workflow.Applications:
            if app.Name is None:
                app.Name = os.path.basename(app.Filepath)
            app.CheckSensible()  # Basic checks against Rank settings that don't make sense

        # Find the correct node type; Map the .cpu, .gpu lists for the nodes
        self.SetNodeLayout(workflow)
        
        # This is Cheeta's basic object for the Applications running. Each can be associated with sweep entites
        self.codes = []
        for app in workflow.Applications:
            code = {}
            code['exe'] = app.Filepath
            code['env'] = None
            #code['runner_override'] = True
            if app.SetupFile is not None:
                code['env_file'] = app.SetupFile
            self.codes += [(app.Name, code)]

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

        SweepGroupLabel = "EFFIS"  # jobname = codar.cheetah.$name-$sweepgroupname
        sweep = codar.cheetah.parameters.Sweep(sweepargs, node_layout=self.node_layout)  # A job can have multiple cheetah sweeps; Each SweepGroup is a job
        sweepgroup = codar.cheetah.parameters.SweepGroup(SweepGroupLabel, walltime=walltime, parameter_groups=[sweep], component_subdirs=workflow.Subdirs, launch_mode=launchmode)
        self.sweeps = [sweepgroup]

        # Job level setup script
        if workflow.SetupFile is not None:
            self.app_config_scripts = {self.machine: os.path.realpath(workflow.SetupFile)}

        """
        if self.config['machine']['submit_setup'] is not None:
            self.run_dir_setup_script = os.path.realpath(self.config['machine']['submit_setup'])
        """            

        # Second argument is appdir (something like place executables are)
        super(Campaign, self).__init__(self.machine, "./")
        self.make_experiment_run_dir(self.output_dir)

        # Set attributes so the user can get the run directories
        workflow.__dict__['Directory'] = os.path.join(self.output_dir, getpass.getuser(), SweepGroupLabel, 'run-0.iteration-0')
        for app in workflow.Applications:
            app.__dict__['Directory'] = workflow.Directory
            if workflow.Subdirs:
                app.__dict__['Directory'] = os.path.join(app.Directory, app.Name)

        InputCopy(workflow)
        for app in workflow.Applications:
            InputCopy(app)