"""Eastmoney native payload contracts. Samples verify individual fields only."""
from .contracts import SourceModule, endpoint, field

KLINE = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
QUOTE = 'https://push2.eastmoney.com/api/qt/stock/get'
DATA = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
SUGGEST = 'https://searchapi.eastmoney.com/api/suggest/get'
NAIVE_TIME = 'Naive source time assigned UTC by current parser; source timezone unverified; date-only precision retained conceptually, no exact publication clock certified.'


def get_module():
    quote_fields = (
        field('data.f43', 'last_price', 'scaled CNY', 'CNY', 'Decimal / 10**f59 (default precision 2)', missing='reject absent', raw_type='number|string'),
        field('data.f169', 'change_amount', 'scaled CNY', 'CNY', 'Decimal / 10**f59 (default precision 2)', missing='reject absent', raw_type='number|string'),
        field('data.f59', 'price_precision (nonpersisted scaling metadata)', 'decimal places', conversion='validated integer 0..8 used for 10**precision price scale; not persisted', missing='default 2 only if absent', raw_type='number|string', normalized_type='int'),
        field('data.f170', 'change_percent', 'hundredths of percentage value', 'percentage_value', 'Decimal / 100; 1.23 means 1.23%', missing='reject absent', raw_type='number|string'),
        field('data.f124', 'snapshot_time', 'Unix seconds or YYYYMMDDhhmmss', 'UTC datetime', 'epoch UTC; 14 digits Asia/Shanghai to UTC', missing='reject absent/zero', raw_type='number|string'),
    )
    lookup = (
        field('QuotationCodeTable.Data[].Code', 'code', missing='lookup requires exact match; search skips absent'),
        field('QuotationCodeTable.Data[].Name', 'name', missing='reject absent'),
        field('QuotationCodeTable.Data[].MktNum', 'market', conversion='1/SH -> SH; 0/2/SZ -> SZ', missing='unsupported rows skipped by search; lookup rejects mismatch'),
        field('QuotationCodeTable.Data[].SecurityTypeName', 'industry', conversion='classification label; not actual business industry'),
    )
    return SourceModule('eastmoney', 'Eastmoney', (
        endpoint('eastmoney', 'announcements', 'https://np-anotice-stock.eastmoney.com/api/security/ann', (
            field('data.list[].title', 'title', conversion='trim', missing='reject absent'),
            field('notice_date|display_time', 'published_at', 'ISO date/datetime', 'UTC datetime', 'fromisoformat; naive assigned UTC', missing='reject absent', verification='unverified'),
            field('art_code', 'url', conversion='https://data.eastmoney.com/notices/detail/{art_code}.html'), field('summary', 'summary'),
        ), time=NAIVE_TIME, limitations=('At most 3 pages by default; empty codes list filtered.',)),
        endpoint('eastmoney', 'news', 'https://search-api-web.eastmoney.com/search/jsonp', (
            field('result.cmsArticleWebOld[].title', 'title', conversion='strip HTML and unescape', missing='reject absent'),
            field('date', 'published_at', 'YYYY-MM-DD HH:MM:SS', 'UTC datetime', 'naive assigned UTC', missing='reject absent', verification='unverified'),
            field('url', 'url'), field('content', 'summary', conversion='strip HTML and unescape'),
        ), payload='JSONP', time=NAIVE_TIME, limitations=('Keyword news relevance is not semantic certification; 3 pages default.',)),
        endpoint('eastmoney', 'price_history', KLINE, (
            field('data.klines[][0]', 'trade_date', 'ISO date', 'date', 'date.fromisoformat', missing='reject malformed row'),
            *(field(f'data.klines[][{index}]', target, 'CNY', conversion='Decimal', missing='reject malformed row') for index, target in ((1,'open_price'),(2,'close_price'),(3,'high_price'),(4,'low_price'))),
            field('data.klines[][5]', 'volume', 'lots', 'shares', 'raw Decimal; aggregate multiplies by 100', missing='reject malformed row', verification='sample_verified'),
            field('data.klines[][6]', 'amount', 'CNY', conversion='Decimal', missing='reject malformed row'),
        ), payload='JSON data.klines array of CSV strings', frequency='daily (klt=101)', time='Trading date only; no intraday timestamp.', basis='forward_adjusted (fqt=1)', limitations=('Resolved index prices use index_points; native index volume units and corporate adjustment remain unverified. Stock/ETF CNY and lot-to-share mapping do not certify index volume.', 'All returned rows required valid; at most request limit, not certified inception coverage.', 'Forward-adjusted close cannot be compared directly with raw fund NAV for premium.')),
        endpoint('eastmoney', 'quote_snapshot', QUOTE, quote_fields, time='f124 source timestamp converted to UTC', basis='snapshot basis unverified', limitations=('Resolved index levels use index_points; stock/ETF levels use CNY. Index adjustment context remains unverified.',)),
        endpoint('eastmoney_intraday', 'quote_snapshot', KLINE, (
            field('data.klines[-1][0]', 'snapshot_time', 'YYYY-MM-DD HH:MM', 'UTC datetime', 'Asia/Shanghai to UTC', missing='reject malformed selected row; complete quote fallback only when no nonempty string kline rows'),
            field('data.klines[-1][2]', 'last_price', 'CNY', conversion='Decimal', missing='reject malformed selected row; complete quote fallback only when no nonempty string kline rows'),
            field('data.prePrice|preKPrice', 'change_amount', 'CNY', 'CNY', 'latest close minus previous close; quantize 0.0001', missing='reject absent/zero previous close', raw_type='number|string'),
            field('data.prePrice|preKPrice + latest close', 'change_percent', 'CNY inputs', 'percentage_value', '(close-previous)/previous*100; quantize 0.0001', missing='reject absent/zero previous close', raw_type='number|string'),
            *quote_fields,
        ), payload='JSON data.klines CSV; complete quote fallback', frequency='minute (klt=1)', time='Asia/Shanghai minute to UTC; fallback f124', basis='forward_adjusted requested (fqt=1); fallback snapshot basis unverified', limitations=('Resolved index levels use index_points; index adjustment context remains unverified.', 'Latest 2 bars requested; only absence of nonempty string kline rows selects complete quote fallback. Malformed selected rows raise. Previous close is never a live price.',)),
        endpoint('eastmoney', 'financial_metrics', DATA, (
            field('result.data[].REPORT_DATE_NAME|DATATYPE', 'report_period', conversion='nonempty REPORT_DATE_NAME preserved verbatim; otherwise DATATYPE year 一季报/半年报/三季报/年报 -> Q1/Q2/Q3/Q4', missing='reject absent'),
            field('TOTAL_OPERATE_INCOME', 'revenue', 'CNY', conversion='optional Decimal', verification='sample_verified', raw_type='number|string'),
            field('PARENT_NETPROFIT', 'net_profit', 'CNY', conversion='optional Decimal; 归母净利润 (profit attributable to parent), not total profit', verification='sample_verified', raw_type='number|string'),
            field('BASIC_EPS', 'eps', 'CNY/share', conversion='optional Decimal', verification='sample_verified', raw_type='number|string'),
            field('WEIGHTAVG_ROE', 'roe', 'percentage_value', conversion='optional Decimal; 16.75 means 16.75%', verification='sample_verified', raw_type='number|string'),
            field('DEBT_ASSET_RATIO', 'debt_to_asset_ratio', 'unverified', conversion='optional Decimal; column not requested', verification='unverified', raw_type='number|string'),
            field('NOTICE_DATE', 'not persisted', 'date/datetime', 'date precision', 'request sorting only; no publication datetime mapping', verification='unverified'),
        ), time='NOTICE_DATE sorts rows; often date-only; parser does not persist publication timestamp.', limitations=('RPT_LICO_FN_CPD; 8 rows default; debt ratio not requested.',)),
        endpoint('eastmoney', 'company_profile', 'https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax', (
            field('jbzl.FULLNAME|gsmc', 'full_name'), field('jbzl.ENAME|ywmc', 'english_name'),
            field('jbzl.REGCAPITAL|zczb (万/亿 suffix)', 'registered_capital', 'CNY 万/亿', 'CNY', 'remove commas; 万 *10000, 亿 *100000000', verification='sample_verified'),
            field('jbzl.REGCAPITAL|zczb (bare numeric)', 'registered_capital', 'unverified', 'unverified', 'Decimal identity; no unit inference', verification='unverified'),
            field('jbzl.FOUNDDATE|clrq', 'establishment_date', 'ISO date', 'date', 'date.fromisoformat'),
            field('jbzl.WEBSITE|gswz', 'website', conversion='prepend https:// if missing scheme'),
            field('jbzl.MAINBUSINESS|zyyw|jyfw|gsjj', 'main_business'),
            field('jbzl.EMPNUM|ygs|gyrs', 'employees', 'persons text', 'persons', 'extract digits; int'),
        ), limitations=('First nonempty alias wins; bare numeric capital unit remains unverified.',)),
        endpoint('eastmoney', 'lookup', SUGGEST, lookup, scope='untracked_homepage/lookup', limitations=('Exact code/market match required; labels do not infer fund type from code prefix.',)),
        endpoint('eastmoney', 'search', SUGGEST, lookup, scope='untracked_homepage/lookup', limitations=('SH/SZ only; de-duplicate market/code; 20 results default.',)),
        endpoint('eastmoney', 'market_index', QUOTE, (
            field('data.f58', 'name', missing='static index name fallback'),
            field('data.f43', 'last_value', 'hundredths of index point', 'index_points', 'Decimal /100', raw_type='number|string'),
            field('data.f169', 'change_amount', 'hundredths of index point', 'index_points', 'Decimal /100', raw_type='number|string'),
            field('data.f170', 'change_percent', 'hundredths of percentage value', 'percentage_value', 'Decimal /100', raw_type='number|string'),
            field('data.f124', 'snapshot_time', 'Unix seconds', 'UTC datetime', 'fromtimestamp UTC', missing='None if absent/zero', raw_type='number|string'),
        ), time='f124 epoch UTC or absent', scope='untracked_homepage/lookup'),
        endpoint('eastmoney', 'macro', DATA, (
            field('NATIONAL_SAME|BASE_SAME|CURRENCY_SAME', 'value', 'percentage_value', conversion='string; CPI/PPI/M2 selected by report', raw_type='number|string'),
            field('MAKE_INDEX', 'value', 'index_points', conversion='string; manufacturing PMI', raw_type='number|string'),
            field('NATIONAL_SEQUENTIAL|BASE_ACCUMULATE|MAKE_SAME|CURRENCY_SEQUENTIAL', 'change_text', 'percentage_value', 'display text', 'prefix label and append %', raw_type='number|string'),
            field('REPORT_DATE', 'published_at', 'ISO date/datetime', 'UTC datetime', 'naive assigned UTC', verification='unverified'),
            field('TIME', 'summary'),
        ), time=NAIVE_TIME, scope='untracked_homepage/lookup', limitations=('Latest row per CPI/PPI/PMI/M2; report period is not exact publication clock.',)),
        endpoint('eastmoney_fund_nav', 'fund_nav', 'https://api.fund.eastmoney.com/f10/lsjz', (
            field('Data.LSJZList[].FSRQ', 'nav_date', 'ISO date', 'date', 'strict date.fromisoformat; sort dates', missing='reject absent or malformed'),
            field('Data.LSJZList[].DWJZ', 'unit_nav', 'CNY/fund_unit', conversion='positive finite Decimal; FundNavRow kind unit_nav', missing='None/empty/-- omitted and missing_nav_value flagged; all unusable rejects fetch', raw_type='string|number', verification='sample_verified'),
            field('Data.LSJZList[].LJJZ', 'cumulative_nav', 'CNY/fund_unit', conversion='positive finite Decimal; FundNavRow kind cumulative_nav', missing='None/empty/-- omitted and missing_nav_value flagged; all unusable rejects fetch', raw_type='string|number', verification='sample_verified'),
            field('PageSize', 'effective_page_size (validation only)', 'records per native page', 'records per native page', 'positive integral <= requested page_size; rows <= echo; short-page detection uses native echo', missing='use requested size if absent', raw_type='number|string', normalized_type='int'),
            field('PageIndex', 'page_index (validation only)', 'page number', 'page number', 'positive integral must equal requested pageIndex; mismatch rejects entire fetch', missing='no echo corroboration if absent', raw_type='number|string', normalized_type='int'),
            field('TotalCount', 'total_count', 'raw NAV date records', conversion='nonnegative integral count', missing='unknown coverage if absent', raw_type='number|string', normalized_type='int'),
            field('absent publication clock', 'published_at', 'unknown', 'unknown', 'None; acquisition time never substitutes', verification='unverified', normalized_type='datetime'),
        ), payload='JSON Data.LSJZList array of objects', frequency='daily', time='NAV valuation date only; publication clock unknown', basis='unknown (valuation_basis official_nav)', scope='managed_security', limitations=('Managed explicit/corroborated ETF/LOF NAV persistence.', 'At most 3 requested pages of up to 100 raw NAV date rows; vendor may clamp native PageSize to 20. Validated native size controls pagination, not the fixed 3-page cap; truncated/unknown coverage explicit. Raw received counts differ from normalized unit/cumulative observations and later writes.', 'Conflicting duplicates or any malformed page reject entire fetch; no partial healthy result.', 'Cumulative NAV is provider cumulative-value series, not reinvested total return. Forward-adjusted prices cannot establish premium.')),
        endpoint('eastmoney_fund_profile', 'fund_profile', 'https://fundf10.eastmoney.com/jbgk_{code}.html', (
            field('recognized fund title|基金代码|基金主代码', 'code (validation only)', conversion='corroborate requested six-digit code; scripts excluded', missing='reject absent/mismatch'),
            field('基金全称', 'full_name', conversion='HTML text/entity normalization', verification='sample_verified'),
            field('基金全称 explicit ETF/交易型开放式/LOF/上市开放式', 'instrument_type', conversion='explicit full-name marker only; 联接/feeder excludes ETF inference, retain unknown unless independent LOF marker; no numeric prefix inference', missing='unknown if no marker'),
            field('基金管理人', 'manager', conversion='HTML text/entity normalization; not fund custodian', verification='sample_verified'),
            field('业绩比较基准', 'benchmark_name', conversion='preserve description; no inferred benchmark code', verification='sample_verified'),
            field('管理费率', 'management_fee', 'annual percentage text', 'fraction', 'finite percentage /100; 0..1', missing='None/empty/-- absent; malformed rejects fetch', verification='sample_verified'),
            field('托管费率', 'custody_fee', 'annual percentage text', 'fraction', 'finite percentage /100; 0..1', missing='None/empty/-- absent; malformed rejects fetch', verification='sample_verified'),
            field('净资产规模|资产规模 explicit 万/亿/元', 'fund_assets', 'CNY suffix text', 'CNY', 'positive finite Decimal times 10000/100000000/1', missing='None if absent or bare unitless number; malformed explicit amount rejects fetch', verification='sample_verified', normalized_type='Decimal'),
            field('净资产规模|资产规模 截止至|截止日期', 'assets_as_of', 'YYYY年MM月DD日|YYYY-MM-DD', 'date', 'calendar date; no publication time inferred', missing='None if absent; invalid date rejects fetch', verification='sample_verified', normalized_type='date'),
        ), payload='HTML table label/value cells and recognized fund title', time='Asset valuation date only if supplied; publication clock unknown', scope='managed_security', limitations=('Managed ETF/LOF profile persistence; generic fund classification resolution is profile-only.', 'No invented benchmark code or prefix-based fund classification; identity-only pages with no usable metadata reject fetch.', 'Fund announcements unavailable: stock-company announcements are not a fund-data substitute; no guessed endpoint.')),

    ), context_units=(('eastmoney', 'price_history', 'index', 'index_points'),
                      ('eastmoney', 'quote_snapshot', 'index', 'index_points'),
                      ('eastmoney_intraday', 'quote_snapshot', 'index', 'index_points')))


def _build(category, constructor=None):
    from app.services import providers
    names = {'announcements': ('RawAnnouncementSourceAdapter','EastmoneyAnnouncementSource'), 'news': ('RawNewsSourceAdapter','EastmoneyNewsSource'), 'price_history': ('RawPriceHistorySourceAdapter','EastmoneyPriceHistorySource'), 'financial_metrics': ('RawFinancialMetricsSourceAdapter','EastmoneyFinancialMetricsSource'), 'company_profile': ('RawCompanyProfileSourceAdapter','EastmoneyCompanyProfileSource'), 'quote_snapshot': ('RawQuoteSnapshotSourceAdapter','EastmoneyQuoteSnapshotSource'), 'intraday_quote': ('RawQuoteSnapshotSourceAdapter','EastmoneyIntradayQuoteSnapshotSource')}
    adapter, provider = names[category]
    return getattr(providers, adapter)('eastmoney_intraday' if category == 'intraday_quote' else 'eastmoney', (constructor or getattr(providers, provider))())


def build_announcement_adapter(constructor=None):
    return _build('announcements', constructor)
def build_news_adapter(constructor=None):
    return _build('news', constructor)
def build_price_history_adapter(constructor=None):
    return _build('price_history', constructor)
def build_financial_adapter(constructor=None):
    return _build('financial_metrics', constructor)
def build_company_profile_adapter(constructor=None):
    return _build('company_profile', constructor)
def build_quote_adapter(constructor=None):
    return _build('quote_snapshot', constructor)
def build_intraday_quote_adapter(constructor=None):
    return _build('intraday_quote', constructor)


def build_lookup_source():
    from app.services.providers.eastmoney_security_lookup import EastmoneySecurityLookupSource
    return EastmoneySecurityLookupSource()


def build_search_source():
    from app.services.providers.eastmoney_security_search import EastmoneySecuritySearchSource
    return EastmoneySecuritySearchSource()


def build_market_index_source():
    from app.services.providers.eastmoney_homepage_overview import EastmoneyMarketIndexSource
    return EastmoneyMarketIndexSource()


def build_macro_source():
    from app.services.providers.eastmoney_homepage_overview import EastmoneyMacroSnapshotSource
    return EastmoneyMacroSnapshotSource()


def build_fund_nav_source():
    from app.services.providers.eastmoney_fund_data import EastmoneyFundNavSource
    return EastmoneyFundNavSource()


def build_fund_profile_source():
    from app.services.providers.eastmoney_fund_data import EastmoneyFundProfileSource
    return EastmoneyFundProfileSource()
