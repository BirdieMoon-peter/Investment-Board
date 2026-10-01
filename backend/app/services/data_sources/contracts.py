"""Declarative parser contracts, independent of runtime fetch health."""
from dataclasses import asdict, dataclass
from typing import Literal

Verification = Literal['parser_contract', 'sample_verified', 'unverified']
IntegrationScope = Literal['managed_security', 'untracked_homepage/lookup', 'planned']


class JsonContract:
    def to_dict(self) -> dict:
        """Return a detached JSON-safe view; modifying it cannot alter the contract."""
        def convert(value):
            if isinstance(value, dict):
                return {key: convert(item) for key, item in value.items()}
            if isinstance(value, (tuple, list)):
                return [convert(item) for item in value]
            return value
        return convert(asdict(self))


@dataclass(frozen=True)
class FieldContract(JsonContract):
    raw_field: str
    target_field: str
    raw_type: str
    raw_unit: str
    normalized_unit: str
    conversion: str
    missing_rule: str
    verification: Verification = 'parser_contract'
    normalized_type: str = 'string'

    def __post_init__(self):
        if self.verification not in ('parser_contract', 'sample_verified', 'unverified'):
            raise ValueError('unknown field verification')


@dataclass(frozen=True)
class EndpointContract(JsonContract):
    key: str
    category: str
    payload_format: str
    endpoint_url: str
    frequency: str
    time_rule: str
    price_basis: str
    fields: tuple[FieldContract, ...]
    integration_scope: IntegrationScope
    limitations: tuple[str, ...]

    def __post_init__(self):
        object.__setattr__(self, 'fields', tuple(self.fields))
        object.__setattr__(self, 'limitations', tuple(self.limitations))
        if not all(isinstance(item, FieldContract) for item in self.fields):
            raise TypeError('fields must contain FieldContract values')
        if not all(isinstance(item, str) for item in self.limitations):
            raise TypeError('limitations must contain strings')
        if self.integration_scope not in ('managed_security', 'untracked_homepage/lookup', 'planned'):
            raise ValueError('unknown integration scope')


@dataclass(frozen=True)
class SourceModule(JsonContract):
    key: str
    name: str
    endpoints: tuple[EndpointContract, ...]
    context_units: tuple[tuple[str, str, str, str], ...] = ()

    def __post_init__(self):
        object.__setattr__(self, 'endpoints', tuple(self.endpoints))
        if not all(isinstance(item, EndpointContract) for item in self.endpoints):
            raise TypeError('endpoints must contain EndpointContract values')
        pairs = [(item.key, item.category) for item in self.endpoints]
        if len(set(pairs)) != len(pairs):
            raise ValueError('duplicate provider/category contract')
        object.__setattr__(self, 'context_units', tuple(tuple(item) for item in self.context_units))
        if any(len(item) != 4 or not all(isinstance(value, str) for value in item) or item[:2] not in pairs for item in self.context_units):
            raise TypeError('context units require declared provider/category and string context/unit')

    def normalized_context_unit(self, provider_key, category, instrument_type):
        return next((unit for key, cat, kind, unit in self.context_units
                     if (key, cat, kind) == (provider_key, category, instrument_type)), None)


def field(raw, target, unit='text', normalized=None, conversion='identity', missing='None if absent', verification='parser_contract', raw_type='string', normalized_type=None):
    if normalized_type is None:
        if target in ('trade_date', 'establishment_date', 'nav_date'):
            normalized_type = 'date'
        elif target in ('published_at', 'snapshot_time'):
            normalized_type = 'datetime'
        elif target == 'employees':
            normalized_type = 'int'
        elif target in ('last_price', 'change_amount', 'change_percent', 'last_value', 'open_price', 'close_price', 'high_price', 'low_price', 'volume', 'amount', 'revenue', 'net_profit', 'eps', 'roe', 'debt_to_asset_ratio', 'registered_capital', 'unit_nav', 'cumulative_nav', 'management_fee', 'custody_fee', 'assets'):
            normalized_type = 'Decimal'
        else:
            normalized_type = 'string'
    return FieldContract(raw, target, raw_type, unit, normalized or unit, conversion, missing, verification, normalized_type)


def endpoint(key, category, url, fields, *, payload='JSON', frequency='on_request', time='not supplied', basis='not_applicable', scope='managed_security', limitations=()):
    return EndpointContract(key, category, payload, url, frequency, time, basis, tuple(fields), scope, tuple(limitations))
