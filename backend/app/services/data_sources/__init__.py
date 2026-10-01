"""Source-owned contracts and lazy builders for existing adapters."""
from .contracts import EndpointContract, FieldContract, SourceModule
from .registry import get_endpoint, get_source_module, list_source_modules

__all__ = ['EndpointContract', 'FieldContract', 'SourceModule', 'get_endpoint', 'get_source_module', 'list_source_modules']
