"""Bounded Eastmoney fund acquisition; raw facts only, no persistence or JS evaluation."""
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from html.parser import HTMLParser
import re
from typing import Literal

import httpx

from app.services.providers.fetch_provenance import SourceAttempt, safe_error_code
from app.services.providers.http_client import build_provider_client

NAV_URL = 'https://api.fund.eastmoney.com/f10/lsjz'
PROFILE_URL = 'https://fundf10.eastmoney.com/jbgk_{code}.html'
_MISSING = {'', '--', '---', '-', '暂无'}


@dataclass(frozen=True)
class FundNavRow:
    nav_date: date
    nav_kind: Literal['unit_nav', 'cumulative_nav']
    value: Decimal
    published_at: datetime | None = None


@dataclass(frozen=True)
class FundMetadata:
    full_name: str | None = None
    instrument_type: Literal['unknown', 'etf', 'lof'] = 'unknown'
    manager: str | None = None
    benchmark_name: str | None = None
    benchmark_code: str | None = None
    management_fee: Decimal | None = None
    custody_fee: Decimal | None = None
    fund_assets: Decimal | None = None
    assets_as_of: date | None = None


@dataclass(frozen=True)
class FundNavFetchResult:
    items: tuple[FundNavRow, ...] = ()
    attempts: tuple[SourceAttempt, ...] = ()
    source_key: str = 'eastmoney_fund_nav'
    received_count: int = 0  # raw NAV date records, not normalized observations or writes
    total_count: int | None = None
    truncated: bool | None = None  # None means provider did not certify coverage
    unit: str = 'CNY/fund_unit'
    frequency: str = 'daily'
    price_basis: str = 'unknown'  # NAV is not a market-price adjustment basis
    valuation_basis: str = 'official_nav'
    missing_nav_count: int = 0
    quality_issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class FundProfileFetchResult:
    item: FundMetadata | None = None
    attempts: tuple[SourceAttempt, ...] = ()
    source_key: str = 'eastmoney_fund_profile'
    received_count: int = 0


def _validate_identifier(code: str, market: str | None):
    if not isinstance(code, str) or not re.fullmatch(r'[0-9]{6}', code):
        raise ValueError('Invalid fund code')
    if market is not None and market not in ('SH', 'SZ'):
        raise ValueError('Invalid fund market')


def _decimal(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError('Invalid numeric field')
    parsed = Decimal(str(value).strip())
    if not parsed.is_finite():
        raise ValueError('Invalid numeric field')
    return parsed


def _optional(value):
    if value is None:
        return None
    text = str(value).strip()
    return None if text in _MISSING else text


def _count(value):
    number = _decimal(value)
    if number < 0 or number != number.to_integral_value():
        raise ValueError('Invalid provider count')
    return int(number)


def _attempt(key, started, received, exc=None, *, has_data=False):
    return SourceAttempt(key, 'failed' if exc else ('succeeded' if has_data else 'empty'),
                         received, error_code=safe_error_code(exc) if exc else None,
                         started_at=started, finished_at=datetime.now(UTC))


class EastmoneyFundNavSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None, max_pages: int = 3, page_size: int = 100):
        if type(max_pages) is not int or not 1 <= max_pages <= 3:
            raise ValueError('Invalid pagination limit')
        if type(page_size) is not int or not 1 <= page_size <= 100:
            raise ValueError('Invalid page size')
        self.transport, self.max_pages, self.page_size = transport, max_pages, page_size

    def fetch(self, code: str, market: str | None = None) -> FundNavFetchResult:
        _validate_identifier(code, market)
        started, received, total = datetime.now(UTC), 0, None
        observations = {}
        missing_nav_count = 0
        dates = set()
        truncated = None
        try:
            with build_provider_client(transport=self.transport) as client:
                for page in range(1, self.max_pages + 1):
                    response = client.get(NAV_URL, params={'fundCode': code, 'pageIndex': page, 'pageSize': self.page_size}, headers={'Referer': 'https://fundf10.eastmoney.com/'})
                    response.raise_for_status()
                    body = response.json(parse_float=Decimal)
                    if not isinstance(body, dict):
                        raise ValueError('Invalid NAV payload')
                    data = body.get('Data')
                    rows = data.get('LSJZList') if isinstance(data, dict) else None
                    if isinstance(rows, list):
                        received += len(rows)
                    if body.get('ErrCode') is not None and _count(body['ErrCode']) != 0:
                        raise ValueError('Provider rejected NAV request')
                    if body.get('Success') is False or body.get('Error') or body.get('ErrMsg'):
                        raise ValueError('Provider rejected NAV request')
                    if not isinstance(rows, list) or len(rows) > self.page_size:
                        raise ValueError('Invalid NAV payload')
                    supplied_total = body.get('TotalCount')
                    if supplied_total is not None:
                        current_total = _count(supplied_total)
                        if total is not None and current_total != total:
                            raise ValueError('Inconsistent NAV count')
                        total = current_total
                    if total is not None and received > total:
                        raise ValueError('Inconsistent NAV count')
                    for raw in rows:
                        if not isinstance(raw, dict) or not isinstance(raw.get('FSRQ'), str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw['FSRQ']):
                            raise ValueError('Invalid NAV row')
                        day = date.fromisoformat(raw['FSRQ'])
                        dates.add(day)
                        for field, kind in (('DWJZ','unit_nav'), ('LJJZ','cumulative_nav')):
                            text = _optional(raw.get(field))
                            if text is None:
                                missing_nav_count += 1
                                continue
                            value = _decimal(text)
                            if value <= 0:
                                raise ValueError('Invalid NAV value')
                            key = (day, kind)
                            if key in observations and observations[key].value != value:
                                raise ValueError('Conflicting NAV duplicate')
                            observations[key] = FundNavRow(day, kind, value)
                    if total is not None and received >= total:
                        truncated = len(dates) < total
                        break
                    if len(rows) < self.page_size:
                        truncated = True if total is not None else None
                        break
                    if page == self.max_pages:
                        truncated = True
            items = tuple(sorted(observations.values(), key=lambda x: (x.nav_date, x.nav_kind != 'unit_nav')))
            if received and not items:
                raise ValueError('No usable NAV values')
            return FundNavFetchResult(items, (_attempt('eastmoney_fund_nav', started, received, has_data=bool(items)),),
                                      received_count=received, total_count=total, truncated=truncated, missing_nav_count=missing_nav_count,
                                      quality_issues=(('missing_nav_value',) if missing_nav_count else ()) +
                                      (('duplicate_nav_date',) if len(dates) < received else ()))
        except Exception as exc:
            return FundNavFetchResult(attempts=(_attempt('eastmoney_fund_nav', started, received, exc),),
                                      received_count=received, total_count=total)


class _ProfileHTML(HTMLParser):
    """Collect table cells/title text; honor optional HTML cell/row end tags."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fields = {}
        self.titles = []
        self.cells = []
        self.cell = None
        self.title = None
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.ignored += 1
        elif not self.ignored:
            if tag == 'title':
                self.title = []
            elif tag == 'tr':
                self._finish_row()
            elif tag in ('td', 'th'):
                self._finish_cell()
                self.cell = []
            elif tag == 'br' and self.cell is not None:
                self.cell.append(' ')

    def handle_data(self, data):
        if not self.ignored:
            if self.cell is not None:
                self.cell.append(data)
            if self.title is not None:
                self.title.append(data)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.ignored = max(0, self.ignored - 1)
        elif not self.ignored:
            if tag in ('td', 'th') and self.cell is not None:
                self._finish_cell()
            elif tag == 'title' and self.title is not None:
                self.titles.append(' '.join(''.join(self.title).split()))
                self.title = None
            elif tag in ('tr', 'table', 'tbody', 'thead', 'tfoot'):
                self._finish_row()

    def _finish_cell(self):
        if self.cell is not None:
            self.cells.append(' '.join(''.join(self.cell).split()))
            self.cell = None

    def _finish_row(self):
        self._finish_cell()
        for index in range(0, len(self.cells) - 1, 2):
            label, value = self.cells[index].rstrip('：:'), self.cells[index + 1]
            if label in self.fields and self.fields[label] != value:
                raise ValueError('Conflicting profile fields')
            self.fields[label] = value
        self.cells = []

    def close(self):
        super().close()
        if not self.ignored:
            self._finish_row()


def _fee(text):
    text = _optional(text)
    if text is None:
        return None
    match = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*%\s*(?:[（(]每年[）)])?', text)
    if not match:
        raise ValueError('Invalid annual fee')
    value = _decimal(match[1]) / 100
    if not 0 <= value <= 1:
        raise ValueError('Invalid annual fee')
    return value


def _assets(text):
    text = _optional(text)
    if text is None:
        return None, None
    match = re.fullmatch(r'([+-]?(?:[\d,]+(?:\.\d*)?|\.\d+))\s*(亿元?|万元?|元)?\s*(?:[（(](?:截止日期|截止至)[：:]\s*([^（）()]+)[）)])?', text)
    if not match:
        raise ValueError('Invalid asset field')
    if ',' in match[1] and not re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?', match[1]):
        raise ValueError('Invalid asset grouping')
    value = _decimal(match[1].replace(',', ''))
    if value < 0 or (match[2] is not None and value == 0):
        raise ValueError('Invalid assets')
    as_of = None
    if match[3]:
        source_date = match[3].strip()
        chinese_date = re.fullmatch(r'(\d{4})年(\d{1,2})月(\d{1,2})日', source_date)
        if chinese_date:
            as_of = date(*map(int, chinese_date.groups()))
        elif re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', source_date):
            as_of = date.fromisoformat(source_date)
        else:
            raise ValueError('Invalid asset date')
    if match[2] is None:
        return None, as_of  # no certified CNY unit for a bare number
    multiplier = Decimal(100000000) if match[2].startswith('亿') else Decimal(10000) if match[2].startswith('万') else Decimal(1)
    return value * multiplier, as_of


def _parse_profile(text, code):
    parser = _ProfileHTML()
    parser.feed(text)
    parser.close()
    fields = parser.fields
    identities = []
    for label in ('基金代码', '基金主代码'):
        if _optional(fields.get(label)):
            match = re.fullmatch(r'([0-9]{6})(?:\s*[（(]主代码[）)])?', fields[label])
            if not match:
                raise ValueError('Invalid fund identity')
            identities.append(match[1])
    for title in parser.titles:
        if '基金' in title and ('概况' in title or '基本信息' in title):
            identities.extend(re.findall(r'(?<![0-9])[0-9]{6}(?![0-9])', title))
    if not identities or any(identity != code for identity in identities):
        raise ValueError('Mismatched fund identity')
    name = _optional(fields.get('基金全称'))
    kind = 'unknown'
    if name:
        feeder = '联接' in name or re.search(r'\bfeeder\b', name, re.IGNORECASE) is not None
        if not feeder and ('ETF' in name.upper() or '交易型开放式' in name):
            kind = 'etf'
        elif 'LOF' in name.upper() or '上市开放式' in name:
            kind = 'lof'
    asset_fields = [_optional(fields.get(label)) for label in ('净资产规模', '资产规模')]
    parsed_assets = [_assets(value) for value in asset_fields if value is not None]
    if len(parsed_assets) > 1 and len(set(parsed_assets)) > 1:
        raise ValueError('Conflicting asset fields')
    assets, as_of = parsed_assets[0] if parsed_assets else (None, None)
    metadata = FundMetadata(name, kind, _optional(fields.get('基金管理人')), _optional(fields.get('业绩比较基准')),
                        management_fee=_fee(fields.get('管理费率')), custody_fee=_fee(fields.get('托管费率')),
                        fund_assets=assets, assets_as_of=as_of)
    if all(value is None for value in (metadata.full_name, metadata.manager, metadata.benchmark_name,
                                      metadata.management_fee, metadata.custody_fee, metadata.fund_assets, metadata.assets_as_of)):
        raise ValueError('No usable fund metadata')
    return metadata


class EastmoneyFundProfileSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self.transport = transport

    def fetch(self, code: str, market: str | None = None) -> FundProfileFetchResult:
        _validate_identifier(code, market)
        started, received = datetime.now(UTC), 0
        try:
            with build_provider_client(transport=self.transport) as client:
                response = client.get(PROFILE_URL.format(code=code))
                response.raise_for_status()
                received = 1
                item = _parse_profile(response.text, code)
            return FundProfileFetchResult(item, (_attempt('eastmoney_fund_profile', started, received, has_data=True),), received_count=received)
        except Exception as exc:
            return FundProfileFetchResult(attempts=(_attempt('eastmoney_fund_profile', started, received, exc),), received_count=received)
