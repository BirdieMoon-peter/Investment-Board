"""Selective security acquisition orchestration; providers are request-local."""
from copy import copy
from app.db.models.data_management import DataSource
from app.services.data_center import SecurityDataCenterService
from app.services.data_source_management import DataSourceManagementService
from app.services.fund_sync import FundSyncService
from app.services.index_data_context import IndexContextProvider
from app.services.providers.stock_data_providers import RawPriceHistorySourceAdapter


def sync_security(session, security_id, body, stock_service, nav_source, profile_source):
    center = SecurityDataCenterService(session)
    security = center.security(security_id)
    kind, origin, manual = center.classification(security)
    generic_fund = security.industry == '基金' and kind == 'unknown' and not manual
    requested = body.categories
    if requested is None:
        requested = ['price_history','quote_snapshot','news','fund_profile','fund_nav'] if kind in {'etf','lof'} or generic_fund or origin == 'fund_profile_unresolved' else ['price_history','quote_snapshot','news'] if kind in {'index','unknown'} else list(stock_service.CATEGORIES)
    requested = list(requested)
    policy = DataSourceManagementService(session)
    fund = FundSyncService(session,center.repository,policy,nav_source,profile_source)
    outcomes = {}
    warnings = []
    # Profile-first is contextual default only. Explicit subsets never introduce an
    # unrequested lookup/profile RPC; profile+NAV is an explicit authorized pair.
    if 'fund_profile' in requested:
        if kind in {'etf','lof'} or generic_fund or origin == 'fund_profile_unresolved':
            outcomes['fund_profile'] = fund.sync(security,'fund_profile',manual=manual)
            kind, origin, manual = center.classification(security)
        else:
            outcomes['fund_profile'] = dict(outcome='not_applicable',received=0,written=0)
    classification_uncertain = 'fund_profile' in outcomes and outcomes['fund_profile'].get('resolved_instrument_type') == 'unknown' and not manual
    if 'fund_nav' in requested:
        outcomes['fund_nav'] = fund.sync(security,'fund_nav',manual=manual) if kind in {'etf','lof'} and not classification_uncertain else dict(outcome='unavailable',reason='ETF/LOF classification required',received=0,written=0)
    stock_categories = [c for c in requested if c in stock_service.CATEGORIES]
    inapplicable = {'announcements','financial_metrics','company_profile'} if kind in {'etf','lof','index'} or generic_fund else set()
    # Unknown objects must not accidentally acquire stock-company semantics.
    if kind == 'unknown':
        inapplicable.update({'announcements','financial_metrics','company_profile'})
    for c in stock_categories:
        if c in inapplicable:
            outcomes[c] = dict(outcome='not_applicable',received=0,written=0)
    stock_categories = [c for c in stock_categories if c not in inapplicable]
    service = copy(stock_service)
    service.disabled_categories = set(stock_service.disabled_categories)
    if 'price_history' in stock_categories:
        dataset = center.repository.get_dataset(security_id,'price_history')
        previous = session.get(DataSource,dataset.source_id) if dataset and dataset.source_id and dataset.price_basis != 'unknown' else None
        preferred = body.price_source or (previous.source_key if previous else 'eastmoney')
        provider, disabled = policy.apply_policy(service.price_history_provider,'price_history',preferred_source=preferred)
        if body.price_source is not None:
            selected_disabled = not policy.effective_enabled(body.price_source, body.price_source)
            matching = [adapter for adapter in getattr(provider, 'raw_sources', ())
                        if isinstance(adapter, RawPriceHistorySourceAdapter) and adapter.name == body.price_source]
            if selected_disabled:
                disabled = True
            elif not matching:
                # Opaque custom providers remain supported for default sync, but
                # cannot establish an explicit source choice or safely fallback.
                reason = 'Selected price source has no selectable source-owned adapter'
                outcomes['price_history'] = dict(outcome='unavailable', reason=reason, received=0, written=0)
                stock_categories.remove('price_history')
                warnings.append('price history unavailable: ' + reason)
            else:
                provider.raw_sources = matching
                if hasattr(provider, 'sources'):
                    provider.sources = []
                disabled = False
        service.price_history_provider = provider
        if disabled:
            service.disabled_categories.add('price_history')
    if kind == 'index':
        for category in ('price_history', 'quote_snapshot'):
            provider = getattr(service, category + '_provider')
            if category in stock_categories and provider is not None:
                setattr(service, category + '_provider', IndexContextProvider(provider, category))
    if stock_categories:
        # Classification controls applicability here, allowing real general fund
        # news without changing the legacy route's historic exclusions.
        result = service.sync_security(security_id,stock_code=security.code,market=security.market,industry=None,categories=stock_categories)
        counts = dict(announcements=result.announcements_upserted, news=result.news_items_upserted, price_history=result.price_bars_upserted, financial_metrics=result.financial_metrics_upserted, quote_snapshot=int(result.quote_snapshot_updated), company_profile=int(result.company_profile_updated))
        for c,v in result.category_outcomes.items():
            outcomes[c] = dict(outcome=v, written=counts[c])
        warnings.extend(result.warnings)
    return dict(security_id=security_id,category_outcomes=outcomes,warnings=warnings,data=center.detail(security_id))
