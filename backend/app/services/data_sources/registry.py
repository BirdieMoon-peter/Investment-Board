"""Fresh immutable catalog reads perform no database access or HTTP requests."""
from . import eastmoney, sina, netease, tencent, ifeng


def list_source_modules():
    return tuple(module.get_module() for module in (eastmoney, sina, netease, tencent, ifeng))


def get_source_module(key: str):
    for module in list_source_modules():
        if module.key == key:
            return module
    raise KeyError(key)


def get_endpoint(vendor_key: str, provider_key: str, category: str):
    for endpoint in get_source_module(vendor_key).endpoints:
        if (endpoint.key, endpoint.category) == (provider_key, category):
            return endpoint
    raise KeyError((vendor_key, provider_key, category))


def normalized_context_unit(provider_key, category, instrument_type):
    for module in list_source_modules():
        unit = module.normalized_context_unit(provider_key, category, instrument_type)
        if unit is not None:
            return unit
    return None
