# Import SubWorkflow to runtime as well, since that's debatably where it better belongs
from effis.composition.workflow import SubWorkflow

# Similarly, need Applications for SubWorkflows
from effis.composition.application import Application

# Also enable the Logger here
from effis.composition.log import CompositionLogger as EffisLogger
#EffisLogger.SetWarning()
