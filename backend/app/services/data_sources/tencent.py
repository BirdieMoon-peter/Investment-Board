"""Tencent currently contributes homepage indices only."""
from .contracts import SourceModule, endpoint, field


def get_module():
    return SourceModule('tencent', 'Tencent', (
        endpoint('tencent', 'market_index', 'https://qt.gtimg.cn/q={symbols}', (
            field('parts[1]', 'name', missing='static name fallback'),
            field('parts[3]', 'last_value', 'index_points', conversion='Decimal', missing='skip missing/nonpositive'),
            field('parts[31]', 'change_amount', 'index_points', conversion='Decimal'),
            field('parts[32]', 'change_percent', 'percentage_value', conversion='Decimal identity'),
            field('parts[30]', 'snapshot_time', 'YYYYMMDDhhmmss', 'UTC datetime', 'Asia/Shanghai to UTC', missing='None if invalid'),
        ), payload='JavaScript assignments of tilde-delimited strings', time='Asia/Shanghai source clock -> UTC', scope='untracked_homepage/lookup', limitations=('No managed-security price-history fetch adapter; isolated unused kline parser is not an endpoint.',)),
    ))


def build_market_index_source():
    from app.services.providers.tencent_market_index import TencentMarketIndexSource
    return TencentMarketIndexSource()
