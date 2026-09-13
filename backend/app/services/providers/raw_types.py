from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class RawAnnouncement:
    title: str
    published_at: datetime
    source: str
    url: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class RawNewsItem:
    title: str
    published_at: datetime
    source: str
    url: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class RawSecurityLookup:
    market: str
    code: str
    name: str
    industry: str | None = None
    status: str = "active"


@dataclass(frozen=True)
class RawPriceBar:
    trade_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    amount: Decimal


@dataclass(frozen=True)
class RawQuoteSnapshot:
    last_price: Decimal
    change_amount: Decimal
    change_percent: Decimal
    snapshot_time: datetime


@dataclass(frozen=True)
class RawFinancialMetrics:
    report_period: str
    revenue: Decimal | None = None
    net_profit: Decimal | None = None
    eps: Decimal | None = None
    roe: Decimal | None = None
    debt_to_asset_ratio: Decimal | None = None


@dataclass(frozen=True)
class RawCompanyProfile:
    full_name: str | None = None
    english_name: str | None = None
    registered_capital: Decimal | None = None
    establishment_date: date | None = None
    website: str | None = None
    main_business: str | None = None
    employees: int | None = None


@dataclass(frozen=True)
class RawMarketIndexSnapshot:
    key: str
    name: str
    market: str | None = None
    last_value: Decimal | None = None
    change_amount: Decimal | None = None
    change_percent: Decimal | None = None
    snapshot_time: datetime | None = None


@dataclass(frozen=True)
class RawMacroSnapshotItem:
    key: str
    title: str
    category: str
    value: str | None = None
    unit: str | None = None
    change_text: str | None = None
    published_at: datetime | None = None
    importance: str = "medium"
    summary: str | None = None
