import codar.savanna

class Node(codar.savanna.machines.MachineNode):
    
    def __init__(self, cores, gpus):
        codar.savanna.machines.MachineNode.__init__(self, cores, gpus)

    def validate_layout(self):
        pass

    def to_json(self):
        self.__dict__['__info_type__'] = 'NodeConfig'
        return self.__dict__