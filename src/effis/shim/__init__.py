# effis.shim
from .nc import nc2bp
from .omas_adios import save_omas_adios
from ..composition.log import CompositionLogger as EffisLogger

from .nimrod_omas import adios_with_omas as NIMROD
