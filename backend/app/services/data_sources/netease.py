"""NetEase units are preserved as unknown unless actually established."""
from .contracts import SourceModule, endpoint, field


def get_module():
    return SourceModule('netease', 'NetEase', (
        endpoint('netease', 'price_history', 'https://api.money.126.net/data/history/{symbol}/day.json', (
            field('data[][0]', 'trade_date', 'date', conversion='slashes to hyphens; date.fromisoformat', missing='reject absent/malformed'),
            *(field(f'data[][{index}]', target, 'unverified', conversion='Decimal identity', missing='reject absent/malformed', verification='unverified', raw_type='number|string') for index,target in ((1,'open_price'),(2,'high_price'),(3,'low_price'),(4,'close_price'),(5,'volume'),(6,'amount'))),
        ), payload='JSON data array of arrays', frequency='daily; 500 rows/page', time='Trading date only', basis='unknown', limitations=('Volume unit and amount availability unverified; aggregate cannot certify shares or adjustment.',)),
        endpoint('netease', 'market_index', 'https://api.money.126.net/data/feed/{symbol}', (
            field('{symbol}.name', 'name', missing='static name fallback'),
            field('{symbol}.price', 'last_value', 'index_points', conversion='Decimal'),
            field('{symbol}.updown', 'change_amount', 'index_points', conversion='Decimal'),
            field('{symbol}.percent', 'change_percent', 'unverified', 'unverified', 'Decimal identity; no percent/fraction scaling inferred', verification='unverified'),
        ), payload='JSONP _ntes_quote_callback', scope='untracked_homepage/lookup', limitations=('No timestamp; exceptions can omit an index. Native percent unit unverified. Not in current default homepage chain.',)),
    ))


def build_price_history_adapter(constructor=None):
    from app.services.providers.stock_data_providers import RawPriceHistorySourceAdapter
    from app.services.providers.netease_price_history import NetEasePriceHistorySource
    return RawPriceHistorySourceAdapter('netease', (constructor or NetEasePriceHistorySource)())


def build_market_index_source():
    from app.services.providers.netease_market_index import NetEaseMarketIndexSource
    return NetEaseMarketIndexSource()
