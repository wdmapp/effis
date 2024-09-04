import codar.savanna

from effis.composition.log import CompositionLogger
import effis.composition.runner
import effis.composition.workflow
import effis.composition.application

import shutil
import socket


class Node(codar.savanna.machines.MachineNode):
    
    def __init__(self, cores=None, gpus=0):
        if cores is None:
            CompositionLogger.RaiseError(ValueError, "Need to set at least number of cores for Node()")
        codar.savanna.machines.MachineNode.__init__(self, cores, gpus)

    def validate_layout(self):
        pass

    def to_json(self):
        self.__dict__['__info_type__'] = 'NodeConfig'
        return self.__dict__


effisnodes =  {
    'perlmutter_cpu': Node(cores=128, gpus=0),
    'perlmutter_cpu_thread': Node(cores=256, gpus=0),
    'perlmutter_gpu': Node(cores=64,  gpus=4),
    'perlmutter_gpu_thread': Node(cores=128,  gpus=4),
    'frontier': Node(cores=64, gpus=8)
}
