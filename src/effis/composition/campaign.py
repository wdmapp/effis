import os
import shutil
from effis.composition.log import CompositionLogger


class Campaign:

    Available = False
    Name = None
    ConfigFile = os.path.expanduser("~/.config/adios2/adios2.yaml")
    ManagerCommand = "hpc_campaign_manager.py"


    def __init__(self, name):

        if name is None:
            pass

        elif not isinstance(name, str):
            CompositionLogger.RaiseError(ValueError, "Can olny set Campaign name with a string")
        
        elif not os.path.exists(self.ConfigFile):
            CompositionLogger.Warning("Can't configure campaign management: {0} does not exist".format(self.ConfigFile))

        elif shutil.which("hpc_campaign_manager.py") is None:
            CompositionLogger.Warning("Can't configure campaign management: {0} is not in $PATH".format(self.ManagerCommand))

        else:
            self.Available = True

        self.Name = name
