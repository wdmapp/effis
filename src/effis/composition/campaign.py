import os
import shutil
import yaml
from effis.composition.log import CompositionLogger


class Campaign:

    Available = False
    Name = None
    ConfigFile = os.path.expanduser("~/.config/adios2/adios2.yaml")
    ManagerCommand = None
    SchemaOnly = False


    def ExistenceChecks(self):

        if not os.path.exists(self.ConfigFile):
            CompositionLogger.Warning("Can't configure campaign management: {0} does not exist".format(self.ConfigFile))
            return False

        if self.ManagerCommand is None :
            default = "hpc_campaign_manager.py"
            self.MangerCommand = shutil.which(default) 
            if self.ManagerCommand is None:
                CompositionLogger.Warning("Can't configure campaign management: {0} is not in $PATH".format(default))
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



    def __init__(self, name, ConfigFile=None, ManagerCommand=None, SchemaOnly=False):

        if isinstance(name, self.__class__):
            self.Available = name.Available
            self.Name = name.Name
            self.ConfigFile = name.ConfigFile
            self.ManagerCommand = name.ManagerCommand
            self.SchemaOnly = name.SchemaOnly

        else:
            self.SchemaOnly = SchemaOnly

            if (ConfigFile is not None) and (not os.path.exists(ConfigFile)):
                CompositionLogger.RaiseError(ValueError, "ConfigFile={0} does not exist.".format(ConfigFile))
            elif ConfigFile is not None:
                self.ConfigFile = ConfigFile

            if (ManagerCommand is not None):
                if os.path.exists(ManagerCommand) or (shutil.which(ManagerCommand) is not None):
                    self.ManagerCommand = ManagerCommand
                else:
                    CompositionLogger.RaiseError(
                        ValueError, 
                        "ManagerCommand={0} is invalid: must be in $PATH or an existing file path".format(ManagerCommand)
                    )

            if (name is not None) and not isinstance(name, str):
                CompositionLogger.RaiseError(ValueError, "Can olny set Campaign name with a string")
            elif name is not None:
                self.Name = name
                self.Available = self.ExistenceChecks()
        
