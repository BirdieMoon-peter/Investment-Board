"""Independent Eastmoney fqt=0 adapter. Legacy fqt=1 tables are never written."""
from datetime import datetime, timezone
from decimal import Decimal
import json
import time
import httpx
from app.services.providers.http_client import DEFAULT_PROVIDER_HEADERS
from app.services.quant.contracts import Acquire, DatasetImport, Bar, MAX_SESSIONS

SOURCE_CONTRACT = {
    'source_key': 'eastmoney', 'adapter': 'quant_raw_daily',
    'native_request': {'klt': '101', 'fqt': '0'},
    'native_fields': ['date', 'open', 'close', 'high', 'low', 'volume_lots', 'amount_CNY'],
    'normalized_price_basis': 'raw', 'currency': 'CNY', 'volume_unit': 'shares',
    'normalization': 'native equity/ETF/LOF lots multiplied by 100 shares; Decimal text',
    'max_sessions': MAX_SESSIONS, 'max_response_bytes_per_security': 2_000_000,
    'timeout_seconds': 5, 'portfolio_deadline_seconds': 20, 'retries': 0,
    'calendar': 'observed_union_of_returned_dates_unless_user_supplies_sessions',
    'coverage': 'bounded_observed_window_not_certified_complete',
    'separation': 'independent_immutable_quant_snapshots_no_legacy_price_writes',
}


class AcquisitionError(ValueError):
    pass


class RawDailySource:
    def __init__(self, transport=None):
        self.transport = transport

    def acquire(self, request: Acquire):
        fetched = []; deadline = time.monotonic() + 20
        with httpx.Client(headers=DEFAULT_PROVIDER_HEADERS.copy(), transport=self.transport, timeout=5, follow_redirects=False) as client:
            for instrument in request.instruments:
                budget = deadline - time.monotonic()
                if budget <= 0:
                    raise AcquisitionError('raw acquisition portfolio deadline exceeded')
                try:
                    with client.stream('GET', 'https://push2his.eastmoney.com/api/qt/stock/kline/get', params={
                        'secid': ('1' if instrument.market == 'SH' else '0') + '.' + instrument.code,
                        'fields1': 'f1,f2,f3,f4,f5,f6', 'fields2': 'f51,f52,f53,f54,f55,f56,f57',
                        'klt': '101', 'fqt': '0', 'lmt': str(MAX_SESSIONS),
                        'beg': request.start_date.strftime('%Y%m%d'), 'end': request.end_date.strftime('%Y%m%d'),
                    }, timeout=min(5, budget)) as response:
                        response.raise_for_status(); content = bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content) > 2_000_000 or time.monotonic() > deadline:
                                raise AcquisitionError('raw acquisition response exceeded bound')
                    payload = json.loads(content, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
                    data = payload['data']
                    if not isinstance(data, dict) or str(data.get('code')) != instrument.code:
                        raise ValueError('source security identity mismatch')
                    rows = data['klines']
                    if not isinstance(rows, list) or not 1 <= len(rows) <= 15000:
                        raise ValueError('invalid native rows')
                    seen = set(); parsed = []
                    for row in rows:
                        if not isinstance(row, str) or len(row) > 500:
                            raise ValueError('invalid native row')
                        fields = row.split(',')
                        if len(fields) < 7:
                            raise ValueError('incomplete native row')
                        bar = Bar(security_id=instrument.security_id, date=fields[0], open=fields[1], close=fields[2], high=fields[3], low=fields[4], volume=str(Decimal(fields[5]) * 100))
                        if bar.date in seen:
                            raise ValueError('duplicate native date')
                        seen.add(bar.date)
                        if request.start_date <= bar.date <= request.end_date:
                            parsed.append(bar)
                    parsed.sort(key=lambda b: b.date)
                    if not parsed:
                        raise ValueError('no bars in requested range')
                    # Vendor may ignore lmt: accepted window is explicitly bounded.
                    fetched.extend(parsed[-MAX_SESSIONS:])
                except (httpx.HTTPError, ValueError, KeyError, TypeError, ArithmeticError):
                    raise AcquisitionError('raw source unavailable or invalid; validated JSON import remains available') from None
        calendar = request.calendar or sorted({bar.date for bar in fetched})[-MAX_SESSIONS:]
        fetched = [bar for bar in fetched if bar.date in calendar]
        return DatasetImport(name=request.name, source='eastmoney_fqt0', retrieved_at=datetime.now(timezone.utc), calendar=calendar, instruments=request.instruments, bars=fetched, corporate_action_coverage=request.corporate_action_coverage, actions=request.actions, calendar_provenance='user_declared_observed_sessions' if request.calendar else 'eastmoney_observed_union_not_certified_exchange_calendar')
