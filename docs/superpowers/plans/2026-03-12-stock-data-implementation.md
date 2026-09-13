# Stock Data Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add historical price data, financial metrics, and company profile information to the Investment Board stock detail page.

**Architecture:** Extend existing stock sync infrastructure with new data providers for historical prices, financial metrics, and company profiles. Reuse aggregate provider pattern and repository layer. Frontend displays new data sections on detail page.

**Tech Stack:** Python FastAPI backend, React TypeScript frontend, SQLModel ORM, existing provider adapter pattern

---

## File Structure

### Backend - New Files
- `backend/app/db/models/price_history.py` - Price history model
- `backend/app/db/models/financial_metrics.py` - Financial metrics model
- `backend/app/db/models/company_profile.py` - Company profile model
- `backend/app/db/repositories/price_history_repository.py` - Price history persistence
- `backend/app/db/repositories/financial_metrics_repository.py` - Financial metrics persistence
- `backend/app/db/repositories/company_profile_repository.py` - Company profile persistence
- `backend/app/services/providers/price_history_provider.py` - Price history aggregate provider
- `backend/app/services/providers/financial_metrics_provider.py` - Financial metrics aggregate provider
- `backend/app/services/providers/company_profile_provider.py` - Company profile aggregate provider
- `backend/app/services/providers/eastmoney_price_history.py` - Eastmoney price history adapter
- `backend/app/services/providers/eastmoney_financial_metrics.py` - Eastmoney financial metrics adapter
- `backend/app/services/providers/eastmoney_company_profile.py` - Eastmoney company profile adapter
- `backend/tests/services/test_eastmoney_price_history.py` - Price history adapter tests
- `backend/tests/services/test_eastmoney_financial_metrics.py` - Financial metrics adapter tests
- `backend/tests/services/test_eastmoney_company_profile.py` - Company profile adapter tests
- `backend/tests/services/test_stock_data_aggregate_providers.py` - Aggregate provider tests
- `backend/tests/api/test_stock_data_sync_api.py` - Stock data sync API tests

### Backend - Modified Files
- `backend/app/db/models/__init__.py` - Export new models
- `backend/app/db/repositories/__init__.py` - Export new repositories
- `backend/app/services/stock_sync.py` - Extend sync service with stock data
- `backend/app/schemas/stock_detail.py` - Add stock data to response schemas
- `backend/app/api/stocks.py` - Wire stock data providers into sync endpoint

### Frontend - New Files
- `frontend/src/components/PriceHistoryChart.tsx` - Price history chart component
- `frontend/src/components/FinancialMetricsPanel.tsx` - Financial metrics display
- `frontend/src/components/CompanyProfilePanel.tsx` - Company profile display
- `frontend/src/components/PriceHistoryChart.test.tsx` - Price history tests
- `frontend/src/components/FinancialMetricsPanel.test.tsx` - Financial metrics tests
- `frontend/src/components/CompanyProfilePanel.test.tsx` - Company profile tests

### Frontend - Modified Files
- `frontend/src/types/watchlist.ts` - Add stock data types
- `frontend/src/pages/StockDetailPage.tsx` - Render new stock data sections

---

## Task 1: Price History Data Model

**Files:**
- Create: `backend/app/db/models/price_history.py`
- Modify: `backend/app/db/models/__init__.py`

- [ ] **Step 1: Write failing test for PriceHistory model**

```python
# backend/tests/db/models/test_price_history.py
from datetime import date
from app.db.models.price_history import PriceHistory

def test_price_history_model_creation():
    price_bar = PriceHistory(
        security_id=1,
        trade_date=date(2026, 3, 10),
        open_price=100.50,
        high_price=102.00,
        low_price=99.80,
        close_price=101.20,
        volume=1000000,
        amount=101000000.00
    )
    assert price_bar.security_id == 1
    assert price_bar.trade_date == date(2026, 3, 10)
    assert price_bar.close_price == 101.20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/models/test_price_history.py::test_price_history_model_creation -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.db.models.price_history'"

- [ ] **Step 3: Implement PriceHistory model**

```python
# backend/app/db/models/price_history.py
from datetime import date
from sqlmodel import Field, SQLModel

class PriceHistory(SQLModel, table=True):
    __tablename__ = "price_history"

    id: int | None = Field(default=None, primary_key=True)
    security_id: int = Field(foreign_key="securities.id", index=True)
    trade_date: date = Field(index=True)
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    amount: float
```

- [ ] **Step 4: Export PriceHistory from models __init__**

```python
# backend/app/db/models/__init__.py (add to existing exports)
from app.db.models.price_history import PriceHistory
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/models/test_price_history.py::test_price_history_model_creation -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/models/price_history.py backend/app/db/models/__init__.py backend/tests/db/models/test_price_history.py
git commit -m "feat: add PriceHistory data model"
```

---

## Task 2: Financial Metrics Data Model

**Files:**
- Create: `backend/app/db/models/financial_metrics.py`
- Modify: `backend/app/db/models/__init__.py`

- [ ] **Step 1: Write failing test for FinancialMetrics model**

```python
# backend/tests/db/models/test_financial_metrics.py
from app.db.models.financial_metrics import FinancialMetrics

def test_financial_metrics_model_creation():
    metrics = FinancialMetrics(
        security_id=1,
        report_period="2025Q4",
        revenue=1000000000.00,
        net_profit=100000000.00,
        eps=1.25,
        roe=0.15,
        debt_to_asset_ratio=0.45
    )
    assert metrics.security_id == 1
    assert metrics.report_period == "2025Q4"
    assert metrics.eps == 1.25
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/models/test_financial_metrics.py::test_financial_metrics_model_creation -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement FinancialMetrics model**

```python
# backend/app/db/models/financial_metrics.py
from sqlmodel import Field, SQLModel

class FinancialMetrics(SQLModel, table=True):
    __tablename__ = "financial_metrics"

    id: int | None = Field(default=None, primary_key=True)
    security_id: int = Field(foreign_key="securities.id", index=True)
    report_period: str = Field(index=True)
    revenue: float | None = None
    net_profit: float | None = None
    eps: float | None = None
    roe: float | None = None
    debt_to_asset_ratio: float | None = None
```

- [ ] **Step 4: Export FinancialMetrics from models __init__**

```python
# backend/app/db/models/__init__.py (add to existing exports)
from app.db.models.financial_metrics import FinancialMetrics
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/models/test_financial_metrics.py::test_financial_metrics_model_creation -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/models/financial_metrics.py backend/app/db/models/__init__.py backend/tests/db/models/test_financial_metrics.py
git commit -m "feat: add FinancialMetrics data model"
```

---

## Task 3: Company Profile Data Model

**Files:**
- Create: `backend/app/db/models/company_profile.py`
- Modify: `backend/app/db/models/__init__.py`

- [ ] **Step 1: Write failing test for CompanyProfile model**

```python
# backend/tests/db/models/test_company_profile.py
from app.db.models.company_profile import CompanyProfile

def test_company_profile_model_creation():
    profile = CompanyProfile(
        security_id=1,
        full_name="平安银行股份有限公司",
        english_name="Ping An Bank Co., Ltd.",
        registered_capital=19405918198.00,
        establishment_date="1987-12-22",
        listing_date="1991-04-03",
        business_scope="吸收公众存款；发放短期、中期和长期贷款...",
        main_business="商业银行业务",
        employees=35000
    )
    assert profile.security_id == 1
    assert profile.full_name == "平安银行股份有限公司"
    assert profile.employees == 35000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/models/test_company_profile.py::test_company_profile_model_creation -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement CompanyProfile model**

```python
# backend/app/db/models/company_profile.py
from sqlmodel import Field, SQLModel

class CompanyProfile(SQLModel, table=True):
    __tablename__ = "company_profiles"

    id: int | None = Field(default=None, primary_key=True)
    security_id: int = Field(foreign_key="securities.id", index=True, unique=True)
    full_name: str | None = None
    english_name: str | None = None
    registered_capital: float | None = None
    establishment_date: str | None = None
    listing_date: str | None = None
    business_scope: str | None = None
    main_business: str | None = None
    employees: int | None = None
```

- [ ] **Step 4: Export CompanyProfile from models __init__**

```python
# backend/app/db/models/__init__.py (add to existing exports)
from app.db.models.company_profile import CompanyProfile
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/models/test_company_profile.py::test_company_profile_model_creation -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/models/company_profile.py backend/app/db/models/__init__.py backend/tests/db/models/test_company_profile.py
git commit -m "feat: add CompanyProfile data model"
```

---

## Task 4: Price History Repository

**Files:**
- Create: `backend/app/db/repositories/price_history_repository.py`
- Modify: `backend/app/db/repositories/__init__.py`

- [ ] **Step 1: Write failing test for PriceHistoryRepository**

```python
# backend/tests/db/repositories/test_price_history_repository.py
from datetime import date
from sqlmodel import Session, create_engine
from app.db.models import Security, PriceHistory
from app.db.repositories.price_history_repository import PriceHistoryRepository

def test_upsert_price_history():
    engine = create_engine("sqlite:///:memory:")
    Security.metadata.create_all(engine)
    PriceHistory.metadata.create_all(engine)

    with Session(engine) as session:
        security = Security(market="SZ", code="000001", name="平安银行", status="active")
        session.add(security)
        session.commit()
        session.refresh(security)

        repo = PriceHistoryRepository(session)
        bars = [
            PriceHistory(
                security_id=security.id,
                trade_date=date(2026, 3, 10),
                open_price=10.50,
                high_price=10.80,
                low_price=10.40,
                close_price=10.70,
                volume=1000000,
                amount=10700000.00
            )
        ]
        result = repo.upsert_many(bars)
        assert len(result) == 1
        assert result[0].close_price == 10.70
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/repositories/test_price_history_repository.py::test_upsert_price_history -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement PriceHistoryRepository**

```python
# backend/app/db/repositories/price_history_repository.py
from datetime import date
from sqlmodel import Session, select
from app.db.models.price_history import PriceHistory

class PriceHistoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_many(self, bars: list[PriceHistory]) -> list[PriceHistory]:
        result = []
        for bar in bars:
            existing = self.session.exec(
                select(PriceHistory).where(
                    PriceHistory.security_id == bar.security_id,
                    PriceHistory.trade_date == bar.trade_date
                )
            ).first()

            if existing:
                existing.open_price = bar.open_price
                existing.high_price = bar.high_price
                existing.low_price = bar.low_price
                existing.close_price = bar.close_price
                existing.volume = bar.volume
                existing.amount = bar.amount
                result.append(existing)
            else:
                self.session.add(bar)
                result.append(bar)

        self.session.commit()
        for bar in result:
            self.session.refresh(bar)
        return result

    def get_recent(self, security_id: int, limit: int = 60) -> list[PriceHistory]:
        return list(
            self.session.exec(
                select(PriceHistory)
                .where(PriceHistory.security_id == security_id)
                .order_by(PriceHistory.trade_date.desc())
                .limit(limit)
            ).all()
        )
```

- [ ] **Step 4: Export PriceHistoryRepository**

```python
# backend/app/db/repositories/__init__.py (add to existing exports)
from app.db.repositories.price_history_repository import PriceHistoryRepository
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/repositories/test_price_history_repository.py::test_upsert_price_history -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/repositories/price_history_repository.py backend/app/db/repositories/__init__.py backend/tests/db/repositories/test_price_history_repository.py
git commit -m "feat: add PriceHistoryRepository"
```

---

## Task 5: Financial Metrics Repository

**Files:**
- Create: `backend/app/db/repositories/financial_metrics_repository.py`
- Modify: `backend/app/db/repositories/__init__.py`

- [ ] **Step 1: Write failing test for FinancialMetricsRepository**

```python
# backend/tests/db/repositories/test_financial_metrics_repository.py
from sqlmodel import Session, create_engine
from app.db.models import Security, FinancialMetrics
from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository

def test_upsert_financial_metrics():
    engine = create_engine("sqlite:///:memory:")
    Security.metadata.create_all(engine)
    FinancialMetrics.metadata.create_all(engine)

    with Session(engine) as session:
        security = Security(market="SZ", code="000001", name="平安银行", status="active")
        session.add(security)
        session.commit()
        session.refresh(security)

        repo = FinancialMetricsRepository(session)
        metrics = [
            FinancialMetrics(
                security_id=security.id,
                report_period="2025Q4",
                revenue=1000000000.00,
                net_profit=100000000.00,
                eps=1.25,
                roe=0.15,
                debt_to_asset_ratio=0.45
            )
        ]
        result = repo.upsert_many(metrics)
        assert len(result) == 1
        assert result[0].eps == 1.25
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/repositories/test_financial_metrics_repository.py::test_upsert_financial_metrics -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement FinancialMetricsRepository**

```python
# backend/app/db/repositories/financial_metrics_repository.py
from sqlmodel import Session, select
from app.db.models.financial_metrics import FinancialMetrics

class FinancialMetricsRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_many(self, metrics: list[FinancialMetrics]) -> list[FinancialMetrics]:
        result = []
        for metric in metrics:
            existing = self.session.exec(
                select(FinancialMetrics).where(
                    FinancialMetrics.security_id == metric.security_id,
                    FinancialMetrics.report_period == metric.report_period
                )
            ).first()

            if existing:
                existing.revenue = metric.revenue
                existing.net_profit = metric.net_profit
                existing.eps = metric.eps
                existing.roe = metric.roe
                existing.debt_to_asset_ratio = metric.debt_to_asset_ratio
                result.append(existing)
            else:
                self.session.add(metric)
                result.append(metric)

        self.session.commit()
        for metric in result:
            self.session.refresh(metric)
        return result

    def get_recent(self, security_id: int, limit: int = 8) -> list[FinancialMetrics]:
        return list(
            self.session.exec(
                select(FinancialMetrics)
                .where(FinancialMetrics.security_id == security_id)
                .order_by(FinancialMetrics.report_period.desc())
                .limit(limit)
            ).all()
        )
```

- [ ] **Step 4: Export FinancialMetricsRepository**

```python
# backend/app/db/repositories/__init__.py (add to existing exports)
from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/repositories/test_financial_metrics_repository.py::test_upsert_financial_metrics -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/repositories/financial_metrics_repository.py backend/app/db/repositories/__init__.py backend/tests/db/repositories/test_financial_metrics_repository.py
git commit -m "feat: add FinancialMetricsRepository"
```

---

## Task 6: Company Profile Repository

**Files:**
- Create: `backend/app/db/repositories/company_profile_repository.py`
- Modify: `backend/app/db/repositories/__init__.py`

- [ ] **Step 1: Write failing test for CompanyProfileRepository**

```python
# backend/tests/db/repositories/test_company_profile_repository.py
from sqlmodel import Session, create_engine
from app.db.models import Security, CompanyProfile
from app.db.repositories.company_profile_repository import CompanyProfileRepository

def test_upsert_company_profile():
    engine = create_engine("sqlite:///:memory:")
    Security.metadata.create_all(engine)
    CompanyProfile.metadata.create_all(engine)

    with Session(engine) as session:
        security = Security(market="SZ", code="000001", name="平安银行", status="active")
        session.add(security)
        session.commit()
        session.refresh(security)

        repo = CompanyProfileRepository(session)
        profile = CompanyProfile(
            security_id=security.id,
            full_name="平安银行股份有限公司",
            english_name="Ping An Bank Co., Ltd.",
            registered_capital=19405918198.00,
            establishment_date="1987-12-22",
            listing_date="1991-04-03",
            business_scope="吸收公众存款；发放短期、中期和长期贷款...",
            main_business="商业银行业务",
            employees=35000
        )
        result = repo.upsert(profile)
        assert result.full_name == "平安银行股份有限公司"
        assert result.employees == 35000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/repositories/test_company_profile_repository.py::test_upsert_company_profile -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement CompanyProfileRepository**

```python
# backend/app/db/repositories/company_profile_repository.py
from sqlmodel import Session, select
from app.db.models.company_profile import CompanyProfile

class CompanyProfileRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert(self, profile: CompanyProfile) -> CompanyProfile:
        existing = self.session.exec(
            select(CompanyProfile).where(
                CompanyProfile.security_id == profile.security_id
            )
        ).first()

        if existing:
            existing.full_name = profile.full_name
            existing.english_name = profile.english_name
            existing.registered_capital = profile.registered_capital
            existing.establishment_date = profile.establishment_date
            existing.listing_date = profile.listing_date
            existing.business_scope = profile.business_scope
            existing.main_business = profile.main_business
            existing.employees = profile.employees
            result = existing
        else:
            self.session.add(profile)
            result = profile

        self.session.commit()
        self.session.refresh(result)
        return result

    def get_by_security_id(self, security_id: int) -> CompanyProfile | None:
        return self.session.exec(
            select(CompanyProfile).where(CompanyProfile.security_id == security_id)
        ).first()
```

- [ ] **Step 4: Export CompanyProfileRepository**

```python
# backend/app/db/repositories/__init__.py (add to existing exports)
from app.db.repositories.company_profile_repository import CompanyProfileRepository
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/db/repositories/test_company_profile_repository.py::test_upsert_company_profile -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/repositories/company_profile_repository.py backend/app/db/repositories/__init__.py backend/tests/db/repositories/test_company_profile_repository.py
git commit -m "feat: add CompanyProfileRepository"
```

---

## Task 7: Raw Types for Stock Data Providers

**Files:**
- Modify: `backend/app/services/providers/raw_types.py`

- [ ] **Step 1: Write failing test for raw stock data types**

```python
# backend/tests/services/providers/test_raw_types.py
from datetime import date
from app.services.providers.raw_types import RawPriceBar, RawFinancialMetrics, RawCompanyProfile

def test_raw_price_bar_creation():
    bar = RawPriceBar(
        trade_date=date(2026, 3, 10),
        open_price=10.50,
        high_price=10.80,
        low_price=10.40,
        close_price=10.70,
        volume=1000000,
        amount=10700000.00
    )
    assert bar.close_price == 10.70

def test_raw_financial_metrics_creation():
    metrics = RawFinancialMetrics(
        report_period="2025Q4",
        revenue=1000000000.00,
        net_profit=100000000.00,
        eps=1.25,
        roe=0.15,
        debt_to_asset_ratio=0.45
    )
    assert metrics.eps == 1.25

def test_raw_company_profile_creation():
    profile = RawCompanyProfile(
        full_name="平安银行股份有限公司",
        english_name="Ping An Bank Co., Ltd.",
        registered_capital=19405918198.00,
        establishment_date="1987-12-22",
        listing_date="1991-04-03",
        business_scope="吸收公众存款...",
        main_business="商业银行业务",
        employees=35000
    )
    assert profile.employees == 35000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/providers/test_raw_types.py -v`
Expected: FAIL with "ImportError: cannot import name 'RawPriceBar'"

- [ ] **Step 3: Add raw stock data types to raw_types.py**

```python
# backend/app/services/providers/raw_types.py (add to existing file)
from datetime import date
from pydantic import BaseModel

class RawPriceBar(BaseModel):
    trade_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    amount: float

class RawFinancialMetrics(BaseModel):
    report_period: str
    revenue: float | None = None
    net_profit: float | None = None
    eps: float | None = None
    roe: float | None = None
    debt_to_asset_ratio: float | None = None

class RawCompanyProfile(BaseModel):
    full_name: str | None = None
    english_name: str | None = None
    registered_capital: float | None = None
    establishment_date: str | None = None
    listing_date: str | None = None
    business_scope: str | None = None
    main_business: str | None = None
    employees: int | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/providers/test_raw_types.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/providers/raw_types.py backend/tests/services/providers/test_raw_types.py
git commit -m "feat: add raw types for stock data providers"
```

---

## Task 8: Eastmoney Price History Adapter

**Files:**
- Create: `backend/app/services/providers/eastmoney_price_history.py`
- Create: `backend/tests/services/test_eastmoney_price_history.py`

- [ ] **Step 1: Write failing test for Eastmoney price history adapter**

```python
# backend/tests/services/test_eastmoney_price_history.py
from app.services.providers.eastmoney_price_history import EastmoneyPriceHistorySource

def test_eastmoney_price_history_fetch():
    source = EastmoneyPriceHistorySource()
    bars = source.fetch(market="SZ", code="000001")
    assert len(bars) > 0
    assert bars[0].close_price > 0
    assert bars[0].volume >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_eastmoney_price_history.py::test_eastmoney_price_history_fetch -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement Eastmoney price history adapter**

```python
# backend/app/services/providers/eastmoney_price_history.py
from datetime import datetime
import httpx
from app.services.providers.raw_types import RawPriceBar

class EastmoneyPriceHistorySource:
    def fetch(self, market: str, code: str, limit: int = 60) -> list[RawPriceBar]:
        secid = f"0.{code}" if market == "SZ" else f"1.{code}"
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
            "klt": "101",  # daily
            "fqt": "1",    # forward adjusted
            "lmt": str(limit),
        }

        try:
            response = httpx.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if data.get("rc") != 0 or "data" not in data or "klines" not in data["data"]:
                raise ValueError("Invalid response from Eastmoney price history API")

            klines = data["data"]["klines"]
            bars = []
            for line in klines:
                parts = line.split(",")
                if len(parts) < 8:
                    continue
                bars.append(
                    RawPriceBar(
                        trade_date=datetime.strptime(parts[0], "%Y-%m-%d").date(),
                        open_price=float(parts[1]),
                        close_price=float(parts[2]),
                        high_price=float(parts[3]),
                        low_price=float(parts[4]),
                        volume=int(parts[5]),
                        amount=float(parts[6]),
                    )
                )
            return bars
        except httpx.HTTPError as exc:
            raise ValueError(f"Failed to fetch price history: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_eastmoney_price_history.py::test_eastmoney_price_history_fetch -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/providers/eastmoney_price_history.py backend/tests/services/test_eastmoney_price_history.py
git commit -m "feat: add Eastmoney price history adapter"
```

---

## Task 9: Eastmoney Financial Metrics Adapter

**Files:**
- Create: `backend/app/services/providers/eastmoney_financial_metrics.py`
- Create: `backend/tests/services/test_eastmoney_financial_metrics.py`

- [ ] **Step 1: Write failing test for Eastmoney financial metrics adapter**

```python
# backend/tests/services/test_eastmoney_financial_metrics.py
from app.services.providers.eastmoney_financial_metrics import EastmoneyFinancialMetricsSource

def test_eastmoney_financial_metrics_fetch():
    source = EastmoneyFinancialMetricsSource()
    metrics = source.fetch(market="SZ", code="000001")
    assert len(metrics) > 0
    assert metrics[0].report_period is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_eastmoney_financial_metrics.py::test_eastmoney_financial_metrics_fetch -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement Eastmoney financial metrics adapter**

```python
# backend/app/services/providers/eastmoney_financial_metrics.py
import httpx
from app.services.providers.raw_types import RawFinancialMetrics

class EastmoneyFinancialMetricsSource:
    def fetch(self, market: str, code: str, limit: int = 8) -> list[RawFinancialMetrics]:
        secid = f"0.{code}" if market == "SZ" else f"1.{code}"
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_LICO_FN_CPD",
            "columns": "SECUCODE,SECURITY_CODE,REPORT_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,BASIC_EPS,WEIGHTAVG_ROE,DEBT_ASSET_RATIO",
            "filter": f"(SECUCODE=\"{secid}\")",
            "pageNumber": "1",
            "pageSize": str(limit),
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
        }

        try:
            response = httpx.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if not data.get("success") or "result" not in data or "data" not in data["result"]:
                raise ValueError("Invalid response from Eastmoney financial metrics API")

            items = data["result"]["data"]
            metrics = []
            for item in items:
                metrics.append(
                    RawFinancialMetrics(
                        report_period=item.get("REPORT_DATE", ""),
                        revenue=item.get("TOTAL_OPERATE_INCOME"),
                        net_profit=item.get("PARENT_NETPROFIT"),
                        eps=item.get("BASIC_EPS"),
                        roe=item.get("WEIGHTAVG_ROE"),
                        debt_to_asset_ratio=item.get("DEBT_ASSET_RATIO"),
                    )
                )
            return metrics
        except httpx.HTTPError as exc:
            raise ValueError(f"Failed to fetch financial metrics: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_eastmoney_financial_metrics.py::test_eastmoney_financial_metrics_fetch -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/providers/eastmoney_financial_metrics.py backend/tests/services/test_eastmoney_financial_metrics.py
git commit -m "feat: add Eastmoney financial metrics adapter"
```

---

## Task 10: Eastmoney Company Profile Adapter

**Files:**
- Create: `backend/app/services/providers/eastmoney_company_profile.py`
- Create: `backend/tests/services/test_eastmoney_company_profile.py`

- [ ] **Step 1: Write failing test for Eastmoney company profile adapter**

```python
# backend/tests/services/test_eastmoney_company_profile.py
from app.services.providers.eastmoney_company_profile import EastmoneyCompanyProfileSource

def test_eastmoney_company_profile_fetch():
    source = EastmoneyCompanyProfileSource()
    profile = source.fetch(market="SZ", code="000001")
    assert profile.full_name is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_eastmoney_company_profile.py::test_eastmoney_company_profile_fetch -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement Eastmoney company profile adapter**

```python
# backend/app/services/providers/eastmoney_company_profile.py
import httpx
from app.services.providers.raw_types import RawCompanyProfile

class EastmoneyCompanyProfileSource:
    def fetch(self, market: str, code: str) -> RawCompanyProfile:
        secid = f"0.{code}" if market == "SZ" else f"1.{code}"
        url = "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/Index"
        params = {"code": secid}

        try:
            response = httpx.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if "jbzl" not in data:
                raise ValueError("Invalid response from Eastmoney company profile API")

            profile_data = data["jbzl"]
            return RawCompanyProfile(
                full_name=profile_data.get("FULLNAME"),
                english_name=profile_data.get("ENAME"),
                registered_capital=profile_data.get("REGCAPITAL"),
                establishment_date=profile_data.get("FOUNDDATE"),
                listing_date=profile_data.get("LISTINGDATE"),
                business_scope=profile_data.get("SCOPE"),
                main_business=profile_data.get("MAINOP"),
                employees=profile_data.get("EMPNUM"),
            )
        except httpx.HTTPError as exc:
            raise ValueError(f"Failed to fetch company profile: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_eastmoney_company_profile.py::test_eastmoney_company_profile_fetch -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/providers/eastmoney_company_profile.py backend/tests/services/test_eastmoney_company_profile.py
git commit -m "feat: add Eastmoney company profile adapter"
```

---

## Task 11: Stock Data Aggregate Providers

**Files:**
- Create: `backend/app/services/providers/stock_data_providers.py`
- Create: `backend/tests/services/test_stock_data_aggregate_providers.py`

- [ ] **Step 1: Write failing test for aggregate price history provider**

```python
# backend/tests/services/test_stock_data_aggregate_providers.py
from app.db.models import PriceHistory
from app.services.providers.stock_data_providers import AggregatePriceHistoryProvider

class MockPriceHistorySource:
    def fetch(self, market: str, code: str, limit: int = 60):
        from datetime import date
        from app.services.providers.raw_types import RawPriceBar
        return [
            RawPriceBar(
                trade_date=date(2026, 3, 10),
                open_price=10.50,
                high_price=10.80,
                low_price=10.40,
                close_price=10.70,
                volume=1000000,
                amount=10700000.00
            )
        ]

def test_aggregate_price_history_provider():
    provider = AggregatePriceHistoryProvider(source=MockPriceHistorySource())
    bars = list(provider.fetch_for_security(security_id=1, market="SZ", code="000001"))
    assert len(bars) == 1
    assert bars[0].security_id == 1
    assert bars[0].close_price == 10.70
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_stock_data_aggregate_providers.py::test_aggregate_price_history_provider -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement aggregate stock data providers**

```python
# backend/app/services/providers/stock_data_providers.py
from collections.abc import Iterable
from app.db.models import PriceHistory, FinancialMetrics, CompanyProfile

class AggregatePriceHistoryProvider:
    def __init__(self, source):
        self.source = source

    def fetch_for_security(
        self, security_id: int, market: str, code: str, limit: int = 60
    ) -> Iterable[PriceHistory]:
        try:
            raw_bars = self.source.fetch(market, code, limit)
            for bar in raw_bars:
                yield PriceHistory(
                    security_id=security_id,
                    trade_date=bar.trade_date,
                    open_price=bar.open_price,
                    high_price=bar.high_price,
                    low_price=bar.low_price,
                    close_price=bar.close_price,
                    volume=bar.volume,
                    amount=bar.amount,
                )
        except Exception:
            return

class AggregateFinancialMetricsProvider:
    def __init__(self, source):
        self.source = source

    def fetch_for_security(
        self, security_id: int, market: str, code: str, limit: int = 8
    ) -> Iterable[FinancialMetrics]:
        try:
            raw_metrics = self.source.fetch(market, code, limit)
            for metric in raw_metrics:
                yield FinancialMetrics(
                    security_id=security_id,
                    report_period=metric.report_period,
                    revenue=metric.revenue,
                    net_profit=metric.net_profit,
                    eps=metric.eps,
                    roe=metric.roe,
                    debt_to_asset_ratio=metric.debt_to_asset_ratio,
                )
        except Exception:
            return

class AggregateCompanyProfileProvider:
    def __init__(self, source):
        self.source = source

    def fetch_for_security(
        self, security_id: int, market: str, code: str
    ) -> CompanyProfile | None:
        try:
            raw_profile = self.source.fetch(market, code)
            return CompanyProfile(
                security_id=security_id,
                full_name=raw_profile.full_name,
                english_name=raw_profile.english_name,
                registered_capital=raw_profile.registered_capital,
                establishment_date=raw_profile.establishment_date,
                listing_date=raw_profile.listing_date,
                business_scope=raw_profile.business_scope,
                main_business=raw_profile.main_business,
                employees=raw_profile.employees,
            )
        except Exception:
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_stock_data_aggregate_providers.py::test_aggregate_price_history_provider -v`
Expected: PASS

- [ ] **Step 5: Add tests for financial metrics and company profile providers**

```python
# backend/tests/services/test_stock_data_aggregate_providers.py (add to existing file)
from app.services.providers.stock_data_providers import AggregateFinancialMetricsProvider, AggregateCompanyProfileProvider

class MockFinancialMetricsSource:
    def fetch(self, market: str, code: str, limit: int = 8):
        from app.services.providers.raw_types import RawFinancialMetrics
        return [
            RawFinancialMetrics(
                report_period="2025Q4",
                revenue=1000000000.00,
                net_profit=100000000.00,
                eps=1.25,
                roe=0.15,
                debt_to_asset_ratio=0.45
            )
        ]

class MockCompanyProfileSource:
    def fetch(self, market: str, code: str):
        from app.services.providers.raw_types import RawCompanyProfile
        return RawCompanyProfile(
            full_name="平安银行股份有限公司",
            english_name="Ping An Bank Co., Ltd.",
            employees=35000
        )

def test_aggregate_financial_metrics_provider():
    provider = AggregateFinancialMetricsProvider(source=MockFinancialMetricsSource())
    metrics = list(provider.fetch_for_security(security_id=1, market="SZ", code="000001"))
    assert len(metrics) == 1
    assert metrics[0].eps == 1.25

def test_aggregate_company_profile_provider():
    provider = AggregateCompanyProfileProvider(source=MockCompanyProfileSource())
    profile = provider.fetch_for_security(security_id=1, market="SZ", code="000001")
    assert profile is not None
    assert profile.employees == 35000
```

- [ ] **Step 6: Run all aggregate provider tests**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_stock_data_aggregate_providers.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/providers/stock_data_providers.py backend/tests/services/test_stock_data_aggregate_providers.py
git commit -m "feat: add aggregate stock data providers"
```

---

## Task 12: Extend Stock Sync Service with Stock Data

**Files:**
- Modify: `backend/app/services/stock_sync.py`
- Create: `backend/tests/services/test_stock_sync_with_data.py`

- [ ] **Step 1: Write failing test for stock sync with stock data**

```python
# backend/tests/services/test_stock_sync_with_data.py
from datetime import date
from sqlmodel import Session, create_engine
from app.db.models import Security, PriceHistory, FinancialMetrics, CompanyProfile
from app.db.repositories import PriceHistoryRepository, FinancialMetricsRepository, CompanyProfileRepository
from app.services.stock_sync import StockSyncService

class MockPriceHistoryProvider:
    def fetch_for_security(self, security_id, market, code, limit=60):
        return [
            PriceHistory(
                security_id=security_id,
                trade_date=date(2026, 3, 10),
                open_price=10.50,
                high_price=10.80,
                low_price=10.40,
                close_price=10.70,
                volume=1000000,
                amount=10700000.00
            )
        ]

class MockFinancialMetricsProvider:
    def fetch_for_security(self, security_id, market, code, limit=8):
        return [
            FinancialMetrics(
                security_id=security_id,
                report_period="2025Q4",
                revenue=1000000000.00,
                net_profit=100000000.00,
                eps=1.25,
                roe=0.15,
                debt_to_asset_ratio=0.45
            )
        ]

class MockCompanyProfileProvider:
    def fetch_for_security(self, security_id, market, code):
        return CompanyProfile(
            security_id=security_id,
            full_name="平安银行股份有限公司",
            employees=35000
        )

class MockAnnouncementProvider:
    def fetch_for_security(self, security_id, since=None):
        return []

class MockNewsProvider:
    def fetch_for_security(self, security_id, since=None):
        return []

def test_stock_sync_with_stock_data():
    engine = create_engine("sqlite:///:memory:")
    Security.metadata.create_all(engine)
    PriceHistory.metadata.create_all(engine)
    FinancialMetrics.metadata.create_all(engine)
    CompanyProfile.metadata.create_all(engine)

    with Session(engine) as session:
        security = Security(market="SZ", code="000001", name="平安银行", status="active")
        session.add(security)
        session.commit()
        session.refresh(security)

        service = StockSyncService(
            announcement_provider=MockAnnouncementProvider(),
            news_provider=MockNewsProvider(),
            announcement_repository=None,
            news_repository=None,
            price_history_provider=MockPriceHistoryProvider(),
            financial_metrics_provider=MockFinancialMetricsProvider(),
            company_profile_provider=MockCompanyProfileProvider(),
            price_history_repository=PriceHistoryRepository(session),
            financial_metrics_repository=FinancialMetricsRepository(session),
            company_profile_repository=CompanyProfileRepository(session),
        )

        from datetime import datetime, timezone
        result = service.sync_security(
            security_id=security.id,
            stock_code=security.code,
            market=security.market,
            synced_at=datetime.now(timezone.utc),
        )

        assert result.price_bars_upserted == 1
        assert result.financial_metrics_upserted == 1
        assert result.company_profile_updated is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_stock_sync_with_data.py::test_stock_sync_with_stock_data -v`
Expected: FAIL with "TypeError: __init__() got unexpected keyword argument 'price_history_provider'"

- [ ] **Step 3: Extend StockSyncService to support stock data providers**

```python
# backend/app/services/stock_sync.py (modify existing class)
# Add new parameters to __init__:
def __init__(
    self,
    *,
    announcement_provider,
    news_provider,
    announcement_repository,
    news_repository,
    price_history_provider=None,
    financial_metrics_provider=None,
    company_profile_provider=None,
    price_history_repository=None,
    financial_metrics_repository=None,
    company_profile_repository=None,
):
    self.announcement_provider = announcement_provider
    self.news_provider = news_provider
    self.announcement_repository = announcement_repository
    self.news_repository = news_repository
    self.price_history_provider = price_history_provider
    self.financial_metrics_provider = financial_metrics_provider
    self.company_profile_provider = company_profile_provider
    self.price_history_repository = price_history_repository
    self.financial_metrics_repository = financial_metrics_repository
    self.company_profile_repository = company_profile_repository
```

- [ ] **Step 4: Extend sync_security method to sync stock data**

```python
# backend/app/services/stock_sync.py (modify sync_security method)
# Add after existing announcement/news sync logic:

price_bars_upserted = 0
financial_metrics_upserted = 0
company_profile_updated = False

if self.price_history_provider and self.price_history_repository:
    try:
        bars = list(self.price_history_provider.fetch_for_security(
            security_id, market, stock_code
        ))
        if bars:
            self.price_history_repository.upsert_many(bars)
            price_bars_upserted = len(bars)
    except Exception as exc:
        warnings.append(f"Price history sync failed: {exc}")

if self.financial_metrics_provider and self.financial_metrics_repository:
    try:
        metrics = list(self.financial_metrics_provider.fetch_for_security(
            security_id, market, stock_code
        ))
        if metrics:
            self.financial_metrics_repository.upsert_many(metrics)
            financial_metrics_upserted = len(metrics)
    except Exception as exc:
        warnings.append(f"Financial metrics sync failed: {exc}")

if self.company_profile_provider and self.company_profile_repository:
    try:
        profile = self.company_profile_provider.fetch_for_security(
            security_id, market, stock_code
        )
        if profile:
            self.company_profile_repository.upsert(profile)
            company_profile_updated = True
    except Exception as exc:
        warnings.append(f"Company profile sync failed: {exc}")

# Update return statement to include new fields
```

- [ ] **Step 5: Update StockSyncResult dataclass**

```python
# backend/app/services/stock_sync.py (modify StockSyncResult)
@dataclass
class StockSyncResult:
    synced: bool
    announcements_upserted: int
    news_items_upserted: int
    price_bars_upserted: int = 0
    financial_metrics_upserted: int = 0
    company_profile_updated: bool = False
    warnings: list[str] = field(default_factory=list)
    synced_at: datetime | None = None
```

- [ ] **Step 6: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/services/test_stock_sync_with_data.py::test_stock_sync_with_stock_data -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/stock_sync.py backend/tests/services/test_stock_sync_with_data.py
git commit -m "feat: extend stock sync service with stock data providers"
```

---

## Task 13: Update Stock Detail Schema with Stock Data

**Files:**
- Modify: `backend/app/schemas/stock_detail.py`

- [ ] **Step 1: Write failing test for extended stock detail schema**

```python
# backend/tests/schemas/test_stock_detail_schema.py
from datetime import date
from app.schemas.stock_detail import StockDetailResponse, PriceBarSchema, FinancialMetricsSchema, CompanyProfileSchema

def test_price_bar_schema():
    bar = PriceBarSchema(
        trade_date=date(2026, 3, 10),
        open_price=10.50,
        high_price=10.80,
        low_price=10.40,
        close_price=10.70,
        volume=1000000,
        amount=10700000.00
    )
    assert bar.close_price == 10.70

def test_financial_metrics_schema():
    metrics = FinancialMetricsSchema(
        report_period="2025Q4",
        revenue=1000000000.00,
        net_profit=100000000.00,
        eps=1.25,
        roe=0.15,
        debt_to_asset_ratio=0.45
    )
    assert metrics.eps == 1.25

def test_company_profile_schema():
    profile = CompanyProfileSchema(
        full_name="平安银行股份有限公司",
        english_name="Ping An Bank Co., Ltd.",
        employees=35000
    )
    assert profile.employees == 35000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/schemas/test_stock_detail_schema.py -v`
Expected: FAIL with "ImportError: cannot import name 'PriceBarSchema'"

- [ ] **Step 3: Add stock data schemas to stock_detail.py**

```python
# backend/app/schemas/stock_detail.py (add to existing file)
from datetime import date
from sqlmodel import SQLModel

class PriceBarSchema(SQLModel):
    trade_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    amount: float

class FinancialMetricsSchema(SQLModel):
    report_period: str
    revenue: float | None = None
    net_profit: float | None = None
    eps: float | None = None
    roe: float | None = None
    debt_to_asset_ratio: float | None = None

class CompanyProfileSchema(SQLModel):
    full_name: str | None = None
    english_name: str | None = None
    registered_capital: float | None = None
    establishment_date: str | None = None
    listing_date: str | None = None
    business_scope: str | None = None
    main_business: str | None = None
    employees: int | None = None
```

- [ ] **Step 4: Extend StockDetailResponse with stock data fields**

```python
# backend/app/schemas/stock_detail.py (modify StockDetailResponse)
class StockDetailResponse(SQLModel):
    security: SecurityDetail
    price_context: list[PriceContextBar]
    announcements: list[AnnouncementItem]
    news: list[NewsItemSchema]
    price_history: list[PriceBarSchema] = []
    financial_metrics: list[FinancialMetricsSchema] = []
    company_profile: CompanyProfileSchema | None = None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/schemas/test_stock_detail_schema.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/stock_detail.py backend/tests/schemas/test_stock_detail_schema.py
git commit -m "feat: extend stock detail schema with stock data"
```

---

## Task 14: Wire Stock Data Providers into Stock Detail API

**Files:**
- Modify: `backend/app/api/stocks.py`
- Create: `backend/tests/api/test_stock_detail_with_data_api.py`

- [ ] **Step 1: Write failing test for stock detail API with stock data**

```python
# backend/tests/api/test_stock_detail_with_data_api.py
from datetime import date
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from app.db.models import Security, PriceHistory, FinancialMetrics, CompanyProfile
from app.main import app

def test_get_stock_detail_with_stock_data():
    engine = create_engine("sqlite:///:memory:")
    Security.metadata.create_all(engine)
    PriceHistory.metadata.create_all(engine)
    FinancialMetrics.metadata.create_all(engine)
    CompanyProfile.metadata.create_all(engine)

    with Session(engine) as session:
        security = Security(market="SZ", code="000001", name="平安银行", status="active")
        session.add(security)
        session.commit()
        session.refresh(security)

        price_bar = PriceHistory(
            security_id=security.id,
            trade_date=date(2026, 3, 10),
            open_price=10.50,
            close_price=10.70,
            high_price=10.80,
            low_price=10.40,
            volume=1000000,
            amount=10700000.00
        )
        session.add(price_bar)

        metrics = FinancialMetrics(
            security_id=security.id,
            report_period="2025Q4",
            revenue=1000000000.00,
            eps=1.25
        )
        session.add(metrics)

        profile = CompanyProfile(
            security_id=security.id,
            full_name="平安银行股份有限公司",
            employees=35000
        )
        session.add(profile)
        session.commit()

    client = TestClient(app)
    response = client.get(f"/api/stocks/{security.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["price_history"]) == 1
    assert data["price_history"][0]["close_price"] == 10.70
    assert len(data["financial_metrics"]) == 1
    assert data["financial_metrics"][0]["eps"] == 1.25
    assert data["company_profile"]["employees"] == 35000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/api/test_stock_detail_with_data_api.py::test_get_stock_detail_with_stock_data -v`
Expected: FAIL with KeyError or missing fields

- [ ] **Step 3: Update stock detail repository to include stock data**

```python
# backend/app/db/repositories/stock_detail_repository.py (modify get_by_security_id)
# Add queries for price_history, financial_metrics, company_profile
# Return extended result with all stock data fields
```

- [ ] **Step 4: Update StockDetailResponse.from_repository_model to map stock data**

```python
# backend/app/schemas/stock_detail.py (modify from_repository_model)
@classmethod
def from_repository_model(cls, detail) -> "StockDetailResponse":
    return cls(
        security=SecurityDetail(...),
        price_context=[...],
        announcements=[...],
        news=[...],
        price_history=[PriceBarSchema(...) for bar in detail.price_history],
        financial_metrics=[FinancialMetricsSchema(...) for m in detail.financial_metrics],
        company_profile=CompanyProfileSchema(...) if detail.company_profile else None,
    )
```

- [ ] **Step 5: Wire stock data providers into sync endpoint dependency**

```python
# backend/app/api/stocks.py (modify get_stock_sync_service)
def get_stock_sync_service(
    session: Session = Depends(get_session),
    aggregate_announcement_provider: AggregateAnnouncementProvider = Depends(...),
    aggregate_news_provider: AggregateNewsProvider = Depends(...),
) -> StockSyncService:
    from app.services.providers.stock_data_providers import (
        AggregatePriceHistoryProvider,
        AggregateFinancialMetricsProvider,
        AggregateCompanyProfileProvider,
    )
    from app.services.providers.eastmoney_price_history import EastmoneyPriceHistorySource
    from app.services.providers.eastmoney_financial_metrics import EastmoneyFinancialMetricsSource
    from app.services.providers.eastmoney_company_profile import EastmoneyCompanyProfileSource
    from app.db.repositories import (
        PriceHistoryRepository,
        FinancialMetricsRepository,
        CompanyProfileRepository,
    )

    return StockSyncService(
        announcement_provider=aggregate_announcement_provider,
        news_provider=aggregate_news_provider,
        announcement_repository=AnnouncementRepository(session),
        news_repository=NewsRepository(session),
        price_history_provider=AggregatePriceHistoryProvider(EastmoneyPriceHistorySource()),
        financial_metrics_provider=AggregateFinancialMetricsProvider(EastmoneyFinancialMetricsSource()),
        company_profile_provider=AggregateCompanyProfileProvider(EastmoneyCompanyProfileSource()),
        price_history_repository=PriceHistoryRepository(session),
        financial_metrics_repository=FinancialMetricsRepository(session),
        company_profile_repository=CompanyProfileRepository(session),
    )
```

- [ ] **Step 6: Update StockSyncResponse schema to include stock data counts**

```python
# backend/app/schemas/stock_detail.py (modify StockSyncResponse)
class StockSyncResponse(SQLModel):
    security_id: int
    synced: bool
    announcements_upserted: int
    news_items_upserted: int
    price_bars_upserted: int = 0
    financial_metrics_upserted: int = 0
    company_profile_updated: bool = False
    warnings: list[str]
    synced_at: datetime
```

- [ ] **Step 7: Update sync endpoint to return extended response**

```python
# backend/app/api/stocks.py (modify sync_stock endpoint return)
return StockSyncResponse.from_service_result(
    security_id=security_id,
    synced=result.synced,
    announcements_upserted=result.announcements_upserted,
    news_items_upserted=result.news_items_upserted,
    price_bars_upserted=result.price_bars_upserted,
    financial_metrics_upserted=result.financial_metrics_upserted,
    company_profile_updated=result.company_profile_updated,
    warnings=result.warnings,
    synced_at=result.synced_at,
)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests/api/test_stock_detail_with_data_api.py::test_get_stock_detail_with_stock_data -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/stocks.py backend/app/db/repositories/stock_detail_repository.py backend/app/schemas/stock_detail.py backend/tests/api/test_stock_detail_with_data_api.py
git commit -m "feat: wire stock data providers into stock detail API"
```

---

## Task 15: Frontend Stock Data Types

**Files:**
- Modify: `frontend/src/types/watchlist.ts`

- [ ] **Step 1: Write failing test for frontend stock data types**

```typescript
// frontend/src/types/watchlist.test.ts
import type { PriceBar, FinancialMetrics, CompanyProfile } from './watchlist'

test('PriceBar type structure', () => {
  const bar: PriceBar = {
    trade_date: '2026-03-10',
    open_price: 10.50,
    high_price: 10.80,
    low_price: 10.40,
    close_price: 10.70,
    volume: 1000000,
    amount: 10700000.00
  }
  expect(bar.close_price).toBe(10.70)
})

test('FinancialMetrics type structure', () => {
  const metrics: FinancialMetrics = {
    report_period: '2025Q4',
    revenue: 1000000000.00,
    net_profit: 100000000.00,
    eps: 1.25,
    roe: 0.15,
    debt_to_asset_ratio: 0.45
  }
  expect(metrics.eps).toBe(1.25)
})

test('CompanyProfile type structure', () => {
  const profile: CompanyProfile = {
    full_name: '平安银行股份有限公司',
    english_name: 'Ping An Bank Co., Ltd.',
    registered_capital: 19405918198.00,
    establishment_date: '1987-12-22',
    listing_date: '1991-04-03',
    business_scope: '吸收公众存款...',
    main_business: '商业银行业务',
    employees: 35000
  }
  expect(profile.employees).toBe(35000)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix "frontend" -- --run src/types/watchlist.test.ts`
Expected: FAIL with "Module not found" or type errors

- [ ] **Step 3: Add stock data types to watchlist.ts**

```typescript
// frontend/src/types/watchlist.ts (add to existing file)
export interface PriceBar {
  trade_date: string
  open_price: number
  high_price: number
  low_price: number
  close_price: number
  volume: number
  amount: number
}

export interface FinancialMetrics {
  report_period: string
  revenue: number | null
  net_profit: number | null
  eps: number | null
  roe: number | null
  debt_to_asset_ratio: number | null
}

export interface CompanyProfile {
  full_name: string | null
  english_name: string | null
  registered_capital: number | null
  establishment_date: string | null
  listing_date: string | null
  business_scope: string | null
  main_business: string | null
  employees: number | null
}
```

- [ ] **Step 4: Extend StockDetailPageData with stock data fields**

```typescript
// frontend/src/types/watchlist.ts (modify StockDetailPageData)
export interface StockDetailPageData {
  security: SecurityDetail
  price_context: PriceContextBar[]
  announcements: Announcement[]
  news: NewsItem[]
  price_history: PriceBar[]
  financial_metrics: FinancialMetrics[]
  company_profile: CompanyProfile | null
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test --prefix "frontend" -- --run src/types/watchlist.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/watchlist.ts frontend/src/types/watchlist.test.ts
git commit -m "feat: add frontend stock data types"
```

---

## Task 16: Price History Chart Component

**Files:**
- Create: `frontend/src/components/PriceHistoryChart.tsx`
- Create: `frontend/src/components/PriceHistoryChart.test.tsx`

- [ ] **Step 1: Write failing test for PriceHistoryChart component**

```typescript
// frontend/src/components/PriceHistoryChart.test.tsx
import { render, screen } from '@testing-library/react'
import { PriceHistoryChart } from './PriceHistoryChart'
import type { PriceBar } from '../types/watchlist'

test('renders price history chart with data', () => {
  const bars: PriceBar[] = [
    {
      trade_date: '2026-03-10',
      open_price: 10.50,
      high_price: 10.80,
      low_price: 10.40,
      close_price: 10.70,
      volume: 1000000,
      amount: 10700000.00
    },
    {
      trade_date: '2026-03-11',
      open_price: 10.70,
      high_price: 10.90,
      low_price: 10.60,
      close_price: 10.85,
      volume: 1200000,
      amount: 13020000.00
    }
  ]

  render(<PriceHistoryChart bars={bars} />)
  expect(screen.getByText(/Price History/i)).toBeInTheDocument()
  expect(screen.getByText(/2026-03-10/)).toBeInTheDocument()
  expect(screen.getByText(/10.70/)).toBeInTheDocument()
})

test('renders empty state when no price history', () => {
  render(<PriceHistoryChart bars={[]} />)
  expect(screen.getByText(/No price history available/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix "frontend" -- --run src/components/PriceHistoryChart.test.tsx`
Expected: FAIL with "Module not found"

- [ ] **Step 3: Implement PriceHistoryChart component**

```typescript
// frontend/src/components/PriceHistoryChart.tsx
import type { PriceBar } from '../types/watchlist'

interface PriceHistoryChartProps {
  bars: PriceBar[]
}

export function PriceHistoryChart({ bars }: PriceHistoryChartProps) {
  if (bars.length === 0) {
    return (
      <section aria-label="Price history">
        <h2>Price History</h2>
        <p>No price history available.</p>
      </section>
    )
  }

  return (
    <section aria-label="Price history">
      <h2>Price History</h2>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Open</th>
            <th>High</th>
            <th>Low</th>
            <th>Close</th>
            <th>Volume</th>
          </tr>
        </thead>
        <tbody>
          {bars.map((bar) => (
            <tr key={bar.trade_date}>
              <td>{bar.trade_date}</td>
              <td>{bar.open_price.toFixed(2)}</td>
              <td>{bar.high_price.toFixed(2)}</td>
              <td>{bar.low_price.toFixed(2)}</td>
              <td>{bar.close_price.toFixed(2)}</td>
              <td>{bar.volume.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix "frontend" -- --run src/components/PriceHistoryChart.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PriceHistoryChart.tsx frontend/src/components/PriceHistoryChart.test.tsx
git commit -m "feat: add PriceHistoryChart component"
```

---

## Task 17: Financial Metrics Panel Component

**Files:**
- Create: `frontend/src/components/FinancialMetricsPanel.tsx`
- Create: `frontend/src/components/FinancialMetricsPanel.test.tsx`

- [ ] **Step 1: Write failing test for FinancialMetricsPanel component**

```typescript
// frontend/src/components/FinancialMetricsPanel.test.tsx
import { render, screen } from '@testing-library/react'
import { FinancialMetricsPanel } from './FinancialMetricsPanel'
import type { FinancialMetrics } from '../types/watchlist'

test('renders financial metrics with data', () => {
  const metrics: FinancialMetrics[] = [
    {
      report_period: '2025Q4',
      revenue: 1000000000.00,
      net_profit: 100000000.00,
      eps: 1.25,
      roe: 0.15,
      debt_to_asset_ratio: 0.45
    }
  ]

  render(<FinancialMetricsPanel metrics={metrics} />)
  expect(screen.getByText(/Financial Metrics/i)).toBeInTheDocument()
  expect(screen.getByText(/2025Q4/)).toBeInTheDocument()
  expect(screen.getByText(/1.25/)).toBeInTheDocument()
})

test('renders empty state when no financial metrics', () => {
  render(<FinancialMetricsPanel metrics={[]} />)
  expect(screen.getByText(/No financial metrics available/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix "frontend" -- --run src/components/FinancialMetricsPanel.test.tsx`
Expected: FAIL with "Module not found"

- [ ] **Step 3: Implement FinancialMetricsPanel component**

```typescript
// frontend/src/components/FinancialMetricsPanel.tsx
import type { FinancialMetrics } from '../types/watchlist'

interface FinancialMetricsPanelProps {
  metrics: FinancialMetrics[]
}

function formatCurrency(value: number | null): string {
  if (value === null) return 'N/A'
  return (value / 100000000).toFixed(2) + '亿'
}

function formatPercent(value: number | null): string {
  if (value === null) return 'N/A'
  return (value * 100).toFixed(2) + '%'
}

export function FinancialMetricsPanel({ metrics }: FinancialMetricsPanelProps) {
  if (metrics.length === 0) {
    return (
      <section aria-label="Financial metrics">
        <h2>Financial Metrics</h2>
        <p>No financial metrics available.</p>
      </section>
    )
  }

  return (
    <section aria-label="Financial metrics">
      <h2>Financial Metrics</h2>
      <table>
        <thead>
          <tr>
            <th>Period</th>
            <th>Revenue</th>
            <th>Net Profit</th>
            <th>EPS</th>
            <th>ROE</th>
            <th>Debt/Asset</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => (
            <tr key={metric.report_period}>
              <td>{metric.report_period}</td>
              <td>{formatCurrency(metric.revenue)}</td>
              <td>{formatCurrency(metric.net_profit)}</td>
              <td>{metric.eps?.toFixed(2) ?? 'N/A'}</td>
              <td>{formatPercent(metric.roe)}</td>
              <td>{formatPercent(metric.debt_to_asset_ratio)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix "frontend" -- --run src/components/FinancialMetricsPanel.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/FinancialMetricsPanel.tsx frontend/src/components/FinancialMetricsPanel.test.tsx
git commit -m "feat: add FinancialMetricsPanel component"
```

---

## Task 18: Company Profile Panel Component

**Files:**
- Create: `frontend/src/components/CompanyProfilePanel.tsx`
- Create: `frontend/src/components/CompanyProfilePanel.test.tsx`

- [ ] **Step 1: Write failing test for CompanyProfilePanel component**

```typescript
// frontend/src/components/CompanyProfilePanel.test.tsx
import { render, screen } from '@testing-library/react'
import { CompanyProfilePanel } from './CompanyProfilePanel'
import type { CompanyProfile } from '../types/watchlist'

test('renders company profile with data', () => {
  const profile: CompanyProfile = {
    full_name: '平安银行股份有限公司',
    english_name: 'Ping An Bank Co., Ltd.',
    registered_capital: 19405918198.00,
    establishment_date: '1987-12-22',
    listing_date: '1991-04-03',
    business_scope: '吸收公众存款；发放短期、中期和长期贷款',
    main_business: '商业银行业务',
    employees: 35000
  }

  render(<CompanyProfilePanel profile={profile} />)
  expect(screen.getByText(/Company Profile/i)).toBeInTheDocument()
  expect(screen.getByText(/平安银行股份有限公司/)).toBeInTheDocument()
  expect(screen.getByText(/35000/)).toBeInTheDocument()
})

test('renders empty state when no company profile', () => {
  render(<CompanyProfilePanel profile={null} />)
  expect(screen.getByText(/No company profile available/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix "frontend" -- --run src/components/CompanyProfilePanel.test.tsx`
Expected: FAIL with "Module not found"

- [ ] **Step 3: Implement CompanyProfilePanel component**

```typescript
// frontend/src/components/CompanyProfilePanel.tsx
import type { CompanyProfile } from '../types/watchlist'

interface CompanyProfilePanelProps {
  profile: CompanyProfile | null
}

export function CompanyProfilePanel({ profile }: CompanyProfilePanelProps) {
  if (!profile) {
    return (
      <section aria-label="Company profile">
        <h2>Company Profile</h2>
        <p>No company profile available.</p>
      </section>
    )
  }

  return (
    <section aria-label="Company profile">
      <h2>Company Profile</h2>
      <dl>
        {profile.full_name && (
          <>
            <dt>Full Name</dt>
            <dd>{profile.full_name}</dd>
          </>
        )}
        {profile.english_name && (
          <>
            <dt>English Name</dt>
            <dd>{profile.english_name}</dd>
          </>
        )}
        {profile.establishment_date && (
          <>
            <dt>Establishment Date</dt>
            <dd>{profile.establishment_date}</dd>
          </>
        )}
        {profile.listing_date && (
          <>
            <dt>Listing Date</dt>
            <dd>{profile.listing_date}</dd>
          </>
        )}
        {profile.employees !== null && (
          <>
            <dt>Employees</dt>
            <dd>{profile.employees.toLocaleString()}</dd>
          </>
        )}
        {profile.main_business && (
          <>
            <dt>Main Business</dt>
            <dd>{profile.main_business}</dd>
          </>
        )}
        {profile.business_scope && (
          <>
            <dt>Business Scope</dt>
            <dd>{profile.business_scope}</dd>
          </>
        )}
      </dl>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix "frontend" -- --run src/components/CompanyProfilePanel.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CompanyProfilePanel.tsx frontend/src/components/CompanyProfilePanel.test.tsx
git commit -m "feat: add CompanyProfilePanel component"
```

---

## Task 19: Integrate Stock Data Components into Stock Detail Page

**Files:**
- Modify: `frontend/src/pages/StockDetailPage.tsx`
- Modify: `frontend/src/pages/StockDetailPage.test.tsx`

- [ ] **Step 1: Write failing test for stock detail page with stock data**

```typescript
// frontend/src/pages/StockDetailPage.test.tsx (add to existing file)
test('renders stock data sections when available', () => {
  const detailWithData: StockDetailPageData = {
    security: {
      security_id: 1,
      market: 'SZ',
      code: '000001',
      name: '平安银行',
      industry: '银行',
      status: 'active'
    },
    price_context: [],
    announcements: [],
    news: [],
    price_history: [
      {
        trade_date: '2026-03-10',
        open_price: 10.50,
        high_price: 10.80,
        low_price: 10.40,
        close_price: 10.70,
        volume: 1000000,
        amount: 10700000.00
      }
    ],
    financial_metrics: [
      {
        report_period: '2025Q4',
        revenue: 1000000000.00,
        net_profit: 100000000.00,
        eps: 1.25,
        roe: 0.15,
        debt_to_asset_ratio: 0.45
      }
    ],
    company_profile: {
      full_name: '平安银行股份有限公司',
      english_name: 'Ping An Bank Co., Ltd.',
      registered_capital: null,
      establishment_date: null,
      listing_date: null,
      business_scope: null,
      main_business: null,
      employees: 35000
    }
  }

  render(
    <StockDetailPage
      detail={detailWithData}
      viewState="ready"
      onBack={() => {}}
    />
  )

  expect(screen.getByText(/Price History/i)).toBeInTheDocument()
  expect(screen.getByText(/Financial Metrics/i)).toBeInTheDocument()
  expect(screen.getByText(/Company Profile/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix "frontend" -- --run src/pages/StockDetailPage.test.tsx`
Expected: FAIL with "Unable to find element"

- [ ] **Step 3: Import stock data components in StockDetailPage**

```typescript
// frontend/src/pages/StockDetailPage.tsx (add imports)
import { PriceHistoryChart } from '../components/PriceHistoryChart'
import { FinancialMetricsPanel } from '../components/FinancialMetricsPanel'
import { CompanyProfilePanel } from '../components/CompanyProfilePanel'
```

- [ ] **Step 4: Add stock data sections to StockDetailPage render**

```typescript
// frontend/src/pages/StockDetailPage.tsx (add after existing sections)
{viewState === 'ready' && currentDetail ? (
  <>
    <QuoteSummary latestBar={currentDetail.price_context[0] ?? null} />
    <PriceContextPanel priceContext={currentDetail.price_context} />
    <PriceHistoryChart bars={currentDetail.price_history} />
    <FinancialMetricsPanel metrics={currentDetail.financial_metrics} />
    <CompanyProfilePanel profile={currentDetail.company_profile} />
    <AnnouncementList announcements={currentDetail.announcements} />
    <NewsList news={currentDetail.news} />
  </>
) : null}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test --prefix "frontend" -- --run src/pages/StockDetailPage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/StockDetailPage.tsx frontend/src/pages/StockDetailPage.test.tsx
git commit -m "feat: integrate stock data components into stock detail page"
```

---

## Task 20: End-to-End Verification

**Files:**
- N/A (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest backend/tests -q`
Expected: All tests pass

- [ ] **Step 2: Run all frontend tests**

Run: `npm test --prefix "frontend" -- --run`
Expected: All tests pass

- [ ] **Step 3: Start backend server**

Run: `cd "backend" && .venv/bin/uvicorn app.main:app --reload`
Expected: Server starts on http://127.0.0.1:8000

- [ ] **Step 4: Start frontend dev server**

Run: `npm run dev --prefix "frontend"`
Expected: Server starts on http://127.0.0.1:5173

- [ ] **Step 5: Manual browser verification**

1. Open http://127.0.0.1:5173
2. Search for a stock (e.g., "000001")
3. Add to watchlist
4. Click on stock to view detail page
5. Click "Sync latest information"
6. Verify price history chart appears
7. Verify financial metrics table appears
8. Verify company profile section appears
9. Verify announcements and news still display

- [ ] **Step 6: Update module documentation**

Update `docs/modules/backend.md` and `docs/modules/frontend.md` with stock data implementation details.

- [ ] **Step 7: Update progress tracking**

Update `memory/progress.md` with completion status.

- [ ] **Step 8: Final commit**

```bash
git add docs/modules/backend.md docs/modules/frontend.md memory/progress.md
git commit -m "docs: update module docs for stock data feature"
```

---

## Plan Complete

All tasks defined for stock data implementation. Ready for execution using superpowers:subagent-driven-development or superpowers:executing-plans.
