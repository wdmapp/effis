import os
import shutil
import yaml
from effis.composition.log import CompositionLogger


class Campaign:

    Available = False
    Name = None
    ConfigFile = os.path.expanduser("~/.config/adios2/adios2.yaml")
    ManagerCommand = "hpc_campaign_manager.py"
    SchemaOnly = False


    def ExistenceChecks(self):

        if not os.path.exists(self.ConfigFile):
            CompositionLogger.Warning("Can't configure campaign management: {0} does not exist".format(self.ConfigFile))
            return False

        if shutil.which("hpc_campaign_manager.py") is None:
            CompositionLogger.Warning("Can't configure campaign management: {0} is not in $PATH".format(self.ManagerCommand))
            return False

        with open(self.ConfigFile, 'r') as infile:
            config = yaml.safe_load(infile)

        if 'Campaign' not in config:
            CompositionLogger.Warning("Key 'Campaign' not found in {0}. Skipping campaign management.".format(self.ConfigFile))
            return False
        elif 'campaignstorepath' not in config['Campaign']:
            CompositionLogger.Warning("Key 'campaignstorepath' not found under 'Campaign' in {0}. Skipping campaign management.".format(self.ConfigFile))
            return False

        return True



    def __init__(self, name, ConfigFile=None, SchemaOnly=False):

        self.SchemaOnly = SchemaOnly

        if (ConfigFile is not None) and (not os.path.exists(ConfigFile)):
            CompositionLogger.RaiseError(ValueError, "ConfigFile={0} does not exist.".format(ConfigFile))
        elif ConfigFile is not None:
            self.ConfigFile = ConfigFile

        if (name is not None) and not isinstance(name, str):
            CompositionLogger.RaiseError(ValueError, "Can olny set Campaign name with a string")
        elif name is not None:
            self.Name = name
            self.Available = self.ExistenceChecks()
        
