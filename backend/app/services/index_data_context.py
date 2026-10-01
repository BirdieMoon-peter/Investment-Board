"""Request-local context normalization for explicitly classified indices only."""
from copy import copy
from dataclasses import replace
from types import SimpleNamespace

from app.services.data_sources.registry import normalized_context_unit
from app.services.providers.stock_data_providers import RawPriceHistorySourceAdapter


class IndexContextProvider:
    def __init__(self, provider, category):
        self.provider, self.category = copy(provider), category
        if category == 'price_history' and hasattr(provider, 'raw_sources'):
            # Equity lot conversion is not certified for index component volume.
            # Retained rows are never migrated or reverse-scaled on this path.
            self.provider.raw_sources = [replace(adapter, volume_unit='unknown')
                if isinstance(adapter, RawPriceHistorySourceAdapter) else adapter
                for adapter in provider.raw_sources]

    def fetch_for_security(self, *args, **kwargs):
        fetched = self.provider.fetch_for_security(*args, **kwargs)
        selected = getattr(fetched, 'source_key', None)
        unit = normalized_context_unit(selected, self.category, 'index')
        issues = list(getattr(fetched, 'quality_issues', ()))
        if unit is None:
            issues.append('unit_unverified')
        issues.append('index_adjustment_context_unverified')
        if self.category == 'price_history':
            issues.append('index_volume_context_unverified')
        values = dict(source_key=selected, attempts=getattr(fetched, 'attempts', ()),
            warnings=getattr(fetched, 'warnings', []), unit=unit,
            frequency=getattr(fetched, 'frequency', None), price_basis='unknown',
            volume_unit=None, amount_available=getattr(fetched, 'amount_available', None),
            quality_issues=tuple(dict.fromkeys(issues)))
        if self.category == 'price_history':
            values['items'] = getattr(fetched, 'items', fetched)
        else:
            values['item'] = getattr(fetched, 'item', fetched)
        return SimpleNamespace(**values)
