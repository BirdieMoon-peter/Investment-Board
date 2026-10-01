"""Sina parser contracts; unsupported amount and timezone remain explicit."""
from .contracts import SourceModule, endpoint, field


def get_module():
    naive = 'Current parser assigns UTC to naive values; source timezone unverified; date-only has no exact publication clock.'
    return SourceModule('sina', 'Sina', (
        endpoint('sina', 'announcements', 'https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllBulletin/stockid/{stock_code}.phtml', (
            field('div.datelist a text', 'title', conversion='join stripped text', missing='reject missing rows/title'),
            field('div.datelist date text', 'published_at', 'ISO date/datetime', 'UTC datetime', 'slashes to hyphens; naive assigned UTC', missing='reject absent', verification='unverified'),
            field('a href', 'url', conversion='urljoin Sina origin'),
        ), payload='HTML', time=naive),
        endpoint('sina', 'news', 'https://finance.sina.com.cn/stock/api/jsonp.php/var%20news=/StockNewsService.getNewsList', (
            field('result.data[]|data[].title', 'title', missing='reject absent'),
            field('result.data[]|data[].ctime', 'published_at', 'YYYY-MM-DD HH:MM:SS', 'UTC datetime', 'naive assigned UTC', missing='reject absent', verification='unverified'),
            field('result.data[]|data[].url', 'url', conversion='urljoin Sina origin', missing='reject absent'), field('result.data[]|data[].intro', 'summary'),
        ), payload='JSON object result.data[] or data[] (response.json parser; no JSONP decoding)', time=naive, limitations=('URL resembles JSONP but parser expects JSON dict; live compatibility unverified.', '3 pages default; keyword results are not relevance certification.')),
        endpoint('sina', 'price_history', 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData', (
            field('day', 'trade_date', 'ISO date', 'date', 'date.fromisoformat', missing='reject absent'),
            *(field(raw, target, 'CNY', conversion='Decimal', missing='reject absent/malformed', raw_type='number|string') for raw,target in (('open','open_price'),('high','high_price'),('low','low_price'),('close','close_price'))),
            field('volume', 'volume', 'shares', conversion='Decimal identity', missing='reject absent', verification='sample_verified', raw_type='number|string'),
            field('(absent)', 'amount', 'unavailable', 'unavailable', 'legacy non-null model stores 0; metadata amount_available=False', missing='unavailable, never a measured zero', verification='unverified'),
        ), payload='JSON array', frequency='daily scale=240', time='Trading date only', basis='unknown', limitations=('Maximum 5000 bars/request; not full-history certification.',)),
        endpoint('sina_fund', 'quote_snapshot', 'https://hq.sinajs.cn/list={market}{code}', (
            field('CSV[3]', 'last_price', 'CNY', conversion='Decimal', missing='reject absent'),
            field('CSV[2],CSV[3]', 'change_amount', 'CNY', conversion='last - previous; quantize 0.0001', missing='reject zero previous close'),
            field('CSV[2],CSV[3]', 'change_percent', 'CNY inputs', 'percentage_value', '(last-previous)/previous*100; quantize 0.0001', missing='reject zero previous close'),
            field('CSV[30],CSV[31]', 'snapshot_time', 'Shanghai date/time', 'UTC datetime', 'Asia/Shanghai to UTC', missing='reject absent/malformed'),
        ), payload='JavaScript assignment of CSV string', time='Source date/time Asia/Shanghai to UTC', basis='snapshot basis unverified', limitations=('Name is legacy provider key; no code-prefix fund classification.',)),
        endpoint('sina', 'market_index', 'https://hq.sinajs.cn/list={symbols}', (
            field('CSV[0]', 'name', missing='static name fallback'),
            field('CSV[1]', 'last_value', 'index_points', conversion='Decimal', missing='skip missing/nonpositive'),
            field('CSV[2]', 'change_amount', 'index_points', conversion='Decimal'),
            field('CSV[3]', 'change_percent', 'percentage_value', conversion='Decimal identity'),
        ), payload='JavaScript assignment of simplified s_ CSV', scope='untracked_homepage/lookup', limitations=('No source timestamp; volume/amount fields unused.',)),
    ))


def _build(category, constructor=None):
    from app.services import providers
    from app.services.providers.sina_price_history import SinaPriceHistorySource
    adapter, source = {'announcements': (providers.RawAnnouncementSourceAdapter, providers.SinaAnnouncementSource), 'news': (providers.RawNewsSourceAdapter, providers.SinaNewsSource), 'price_history': (providers.RawPriceHistorySourceAdapter, SinaPriceHistorySource), 'quote_snapshot': (providers.RawQuoteSnapshotSourceAdapter, providers.SinaFundQuoteSnapshotSource)}[category]
    return adapter('sina_fund' if category == 'quote_snapshot' else 'sina', (constructor or source)())


def build_announcement_adapter(constructor=None):
    return _build('announcements', constructor)
def build_news_adapter(constructor=None):
    return _build('news', constructor)
def build_price_history_adapter(constructor=None):
    return _build('price_history', constructor)
def build_quote_adapter(constructor=None):
    return _build('quote_snapshot', constructor)


def build_market_index_source():
    from app.services.providers.sina_market_index import SinaMarketIndexSource
    return SinaMarketIndexSource()
