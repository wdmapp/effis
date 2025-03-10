import os
import shutil
import yaml
from effis.composition.log import CompositionLogger


class Campaign:

    Available = False
    Name = None
    ConfigFile = os.path.expanduser("~/.config/adios2/adios2.yaml")
    ManagerCommand = "hpc_campaign_manager.py"


    def __init__(self, name):

        self.Name = name

        if name is None:
            pass

        elif not isinstance(name, str):
            CompositionLogger.RaiseError(ValueError, "Can olny set Campaign name with a string")
        
        elif not os.path.exists(self.ConfigFile):
            CompositionLogger.Warning("Can't configure campaign management: {0} does not exist".format(self.ConfigFile))

        elif shutil.which("hpc_campaign_manager.py") is None:
            CompositionLogger.Warning("Can't configure campaign management: {0} is not in $PATH".format(self.ManagerCommand))

        else:
            with open(self.ConfigFile, 'r') as infile:
                config = yaml.safe_load(infile)

            if 'Campaign' not in config:
                CompositionLogger.Warning("Key 'Campaign' not found in {0}. Skipping campaign management.".format(self.ConfigFile))
            elif 'campaignstorepath' not in config['Campaign']:
                CompositionLogger.Warning("Key 'campaignstorepath' not found under 'Campaign' in {0}. Skipping campaign management.".format(self.ConfigFile))
            else:
                self.Available = True


