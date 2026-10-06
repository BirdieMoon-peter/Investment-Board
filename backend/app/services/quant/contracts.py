"""Strict, bounded raw-data and experiment contracts. Decimal values stay strings."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, BeforeValidator

MAX_SESSIONS = 600
MAX_INSTRUMENTS = 8


def today():
    return datetime.now(timezone(timedelta(hours=8))).date()


def decimal_input(value):
    if not isinstance(value, (str, Decimal)) or len(str(value)) > 60:
        raise ValueError('Decimal must be a finite string of at most 60 characters')
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError('invalid decimal') from None
    if not number.is_finite() or abs(number) > Decimal('1e15') or (number and number.adjusted() < -20):
        raise ValueError('decimal outside supported finite precision range')
    return number


def date_input(value):
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError('date must be YYYY-MM-DD')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('date must be YYYY-MM-DD')
    return parsed


ISODate = Annotated[date, BeforeValidator(date_input)]
StrictID = Annotated[int, Field(strict=True, gt=0)]


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Instrument(Strict):
    security_id: int = Field(gt=0, strict=True)
    market: Literal['SH', 'SZ']
    code: str = Field(pattern=r'^\d{6}$')
    name: str = Field(min_length=1, max_length=100)
    instrument_type: Literal['a_share', 'etf', 'lof']
    lot_size: int = Field(default=100, gt=0, le=10000, strict=True)
    settlement_lag: int = Field(default=1, ge=0, le=1, strict=True)
    limit_pct: Decimal | None = Field(default=None, gt=0, le=Decimal('1'))
    _decimal = field_validator('limit_pct', mode='before')(lambda v: None if v is None else decimal_input(v))


class Bar(Strict):
    security_id: int = Field(gt=0, strict=True)
    date: ISODate
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)
    _decimal = field_validator('open', 'high', 'low', 'close', 'volume', mode='before')(decimal_input)

    @model_validator(mode='after')
    def valid(self):
        if self.date > today() or not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError('future or invalid OHLC bar')
        return self


class Action(Strict):
    security_id: int = Field(gt=0, strict=True)
    date: ISODate
    kind: Literal['cash_dividend', 'split']
    value: Decimal = Field(gt=0)
    cash_available_date: ISODate | None = None
    _decimal = field_validator('value', mode='before')(decimal_input)

    @model_validator(mode='after')
    def valid(self):
        if self.kind == 'cash_dividend' and (self.cash_available_date is None or self.cash_available_date < self.date):
            raise ValueError('cash availability required on/after dividend date')
        if self.kind == 'split' and self.cash_available_date is not None:
            raise ValueError('split has no cash availability date')
        return self


class DatasetImport(Strict):
    name: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)
    retrieved_at: datetime
    price_basis: Literal['raw'] = 'raw'
    currency: Literal['CNY'] = 'CNY'
    volume_unit: Literal['shares'] = 'shares'
    calendar: list[ISODate] = Field(min_length=2, max_length=MAX_SESSIONS)
    instruments: list[Instrument] = Field(min_length=1, max_length=MAX_INSTRUMENTS)
    bars: list[Bar] = Field(min_length=2, max_length=MAX_SESSIONS * MAX_INSTRUMENTS)
    corporate_action_coverage: Literal['unknown', 'declared_complete', 'declared_none'] = 'unknown'
    actions: list[Action] = Field(default_factory=list, max_length=100)
    calendar_provenance: str = Field(default='user_declared_observed_sessions', min_length=1, max_length=200)

    @field_validator('retrieved_at', mode='before')
    @classmethod
    def timestamp_input(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError('retrieval timestamp must be an ISO timezone timestamp')
        return value

    @model_validator(mode='after')
    def valid(self):
        if self.retrieved_at.tzinfo is None or self.retrieved_at > datetime.now(timezone.utc):
            raise ValueError('retrieval timestamp must have timezone and cannot be future')
        if self.calendar != sorted(set(self.calendar)) or self.calendar[-1] > today():
            raise ValueError('calendar must contain unique ascending non-future sessions')
        ids = [i.security_id for i in self.instruments]
        if len(set(ids)) != len(ids) or len({(i.market, i.code) for i in self.instruments}) != len(ids):
            raise ValueError('duplicate instrument identity')
        pairs = [(b.security_id, b.date) for b in self.bars]
        if len(set(pairs)) != len(pairs) or any(i not in ids or d not in self.calendar for i, d in pairs):
            raise ValueError('duplicate bar or bar outside universe/calendar')
        if set(i for i, _ in pairs) != set(ids):
            raise ValueError('each instrument requires bars')
        actions = [(a.security_id, a.date, a.kind) for a in self.actions]
        if len(set(actions)) != len(actions):
            raise ValueError('duplicate corporate action')
        for action in self.actions:
            if action.security_id not in ids or action.date not in self.calendar or (action.cash_available_date is not None and action.cash_available_date not in self.calendar):
                raise ValueError('action dates must be explicit observed sessions')
        if self.corporate_action_coverage == 'declared_none' and self.actions:
            raise ValueError('declared_none cannot contain actions')
        self.bars.sort(key=lambda b: (b.date, b.security_id))
        self.actions.sort(key=lambda a: (a.date, a.security_id, a.kind))
        self.instruments.sort(key=lambda i: i.security_id)
        return self


PARAMETERS = {
    'etf_momentum': {'lookback': (2, 252, 20), 'top_k': (1, 8, 1), 'rebalance_every': (1, 60, 5)},
    'ma_trend': {'ma_window': (2, 252, 20), 'rebalance_every': (1, 60, 1)},
    'etf_mean_reversion': {'ma_window': (2, 252, 20), 'rebalance_every': (1, 60, 1), 'entry_deviation': ('-0.5', '-0.001', '-0.05'), 'exit_deviation': ('0', '0.5', '0')},
}


class StrategyCreate(Strict):
    name: str = Field(min_length=1, max_length=100)
    template: Literal['etf_momentum', 'ma_trend', 'etf_mean_reversion']
    universe: list[StrictID] = Field(min_length=1, max_length=MAX_INSTRUMENTS)
    parameters: dict = Field(default_factory=dict)
    max_exposure: Decimal = Field(default=Decimal('1'), gt=0, le=1)
    parent_id: int | None = Field(default=None, gt=0, strict=True)
    _decimal = field_validator('max_exposure', mode='before')(decimal_input)

    @model_validator(mode='after')
    def valid(self):
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 1 for x in self.universe) or len(set(self.universe)) != len(self.universe):
            raise ValueError('invalid universe')
        spec = PARAMETERS[self.template]
        if set(self.parameters) - set(spec):
            raise ValueError('unknown template parameter')
        parameters = {}
        for key, (low, high, default) in spec.items():
            value = self.parameters.get(key, default)
            if isinstance(default, int):
                if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                    raise ValueError('invalid integer parameter')
            else:
                value = decimal_input(value)
                if not Decimal(low) <= value <= Decimal(high):
                    raise ValueError('invalid deviation parameter')
                value = str(value)
            parameters[key] = value
        if parameters.get('top_k', 1) > len(self.universe):
            raise ValueError('top_k exceeds universe')
        self.universe.sort(); self.parameters = parameters
        return self


class Costs(Strict):
    commission_rate: Decimal = Field(default=Decimal('0.0003'), ge=0, le=Decimal('0.1'))
    minimum_commission: Decimal = Field(default=Decimal('5'), ge=0, le=1000)
    sell_tax: Decimal = Field(default=Decimal('0.0005'), ge=0, le=Decimal('0.1'))
    slippage: Decimal = Field(default=Decimal('0.0005'), ge=0, le=Decimal('0.1'))
    volume_cap: Decimal = Field(default=Decimal('0.05'), gt=0, le=1)
    _decimal = field_validator('commission_rate', 'minimum_commission', 'sell_tax', 'slippage', 'volume_cap', mode='before')(decimal_input)


class RunCreate(Strict):
    strategy_id: int = Field(gt=0, strict=True)
    dataset_id: int = Field(gt=0, strict=True)
    initial_cash: Decimal = Field(default=Decimal('100000'), gt=0, le=Decimal('1e12'))
    costs: Costs = Field(default_factory=Costs)
    holdout_date: ISODate | None = None
    _decimal = field_validator('initial_cash', mode='before')(decimal_input)


class AccountCreate(RunCreate):
    name: str = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def no_holdout(self):
        if self.holdout_date is not None:
            raise ValueError('paper accounts have no historical holdout')
        return self


class Advance(Strict):
    expected_version: int = Field(gt=0, strict=True)
    dataset_id: int = Field(gt=0, strict=True)


class Review(Strict):
    status: Literal['unreviewed', 'reviewed', 'invalidated']
    note: str = Field(default='', max_length=4000)
    research_project_id: int | None = Field(default=None, gt=0, strict=True)
    hypothesis: str = Field(default='', max_length=4000)


class Generate(Strict):
    critique: bool = Field(default=False, strict=True)


class Acquire(Strict):
    name: str = Field(min_length=1, max_length=100)
    instruments: list[Instrument] = Field(min_length=1, max_length=MAX_INSTRUMENTS)
    start_date: ISODate
    end_date: ISODate
    corporate_action_coverage: Literal['unknown', 'declared_complete', 'declared_none'] = 'unknown'
    actions: list[Action] = Field(default_factory=list, max_length=100)
    calendar: list[ISODate] | None = Field(default=None, min_length=2, max_length=MAX_SESSIONS)

    @model_validator(mode='after')
    def valid(self):
        if self.start_date > self.end_date or self.end_date > today() or (self.end_date - self.start_date).days > 1500:
            raise ValueError('acquisition range must be non-future and at most 1500 days')
        return self
