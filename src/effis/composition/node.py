import codar.savanna
from effis.composition.log import CompositionLogger

"""
def GetNodeType(machine, wfnode=None):
    NodeName = "{0}Node".format(machine.capitalize())
    if wfnode is not None:
        NodeType = wfnode
    elif NodeName in codar.savanna.machines.__dict__:
        NodeType = codar.savanna.machines.__dict__[NodeName]()
    elif machine.lower() in effis.composition.node.effisnodes:
        NodeType = effis.composition.node.effisnodes[machine.lower()]
    else:
        CompositionLogger.RaiseError(ValueError, "Could not find a MachineNode for {0}. Please set an effis.composition.Node".format(machine))
    return NodeType
"""


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
    'perlmutter_gpu': Node(cores=64,  gpus=4),
}
