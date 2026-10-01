# Data source contracts

Vendor-owned modules in `backend/app/services/data_sources/` describe native payloads and their current normalized mappings. Read the catalog with `list_source_modules()`, `get_source_module(vendor_key)` or `get_endpoint(vendor_key, provider_key, category)`. Reads return fresh frozen dataclasses with tuple collections, perform no network/database access, and reject unknown keys with `KeyError`. `to_dict()` produces a detached JSON-safe view.

## Capability and integration boundaries

| Vendor | Managed security acquisition adapters | Other implemented parsers | Planned integration |
|---|---|---|---|
| Eastmoney | Announcements, news, daily prices, intraday/quote snapshots, financial metrics, company profile; explicit ETF/LOF NAV/profile | Security search/lookup, homepage indices and macro snapshots | Fund announcements |
| Sina | Announcements, news, daily prices, quote snapshot | Homepage indices | None declared |
| NetEase | Daily price history fallback (after Sina/Eastmoney) | Homepage index parser (not in current default homepage chain) | None declared |
| Tencent | None | Homepage indices | Managed history unavailable; a standalone kline parsing helper does not implement a fetch endpoint |
| Ifeng | None | News HTML parser | Stock-news integration; not in the default sync chain |

`managed_security` means the adapter participates in stock-sync factories or the managed ETF/LOF data-center chain. `untracked_homepage/lookup` identifies homepage or identity helpers outside managed acquisition telemetry. `planned` identifies future integration; fund announcements await a verified fund-specific contract, while Ifeng has an existing parser without default integration. Capabilities describe code, not live availability or completeness.

Stock factory order is announcements Eastmoney → Sina; news Eastmoney → Sina; history Sina → Eastmoney → NetEase; quote Eastmoney intraday → Eastmoney snapshot → Sina quote; financial/profile Eastmoney. Each factory builds fresh adapters. Existing dependency function signatures and patchable provider constructors remain compatible. A category/provider pair identifies an endpoint; the same provider key can appear in multiple categories.

## Units, precision and missing values

| Dataset | Native representation | Normalized representation | Boundary |
|---|---|---|---|
| Eastmoney daily price | `data.klines` CSV: date, open, close, high, low, volume, amount; `klt=101`, `fqt=1` | Decimal CNY prices/amount; volume lots ×100 → shares in aggregate adapter | Forward-adjusted series; cannot directly calculate premium against raw fund NAV |
| Sina daily price | JSON array with `day/open/high/low/close/volume` | Decimal prices; volume shares unchanged | Price adjustment unknown; amount unavailable, legacy stored zero is not measured turnover |
| NetEase daily history | Arrays: date, open, high, low, close, volume, amount | Decimal identity | Volume/amount units and adjustment remain unverified |
| Current quote percentage and ROE | Decimal percentage values after quote scaling | `1.23` means `1.23%`; `16.75` ROE means `16.75%` | Do not divide these fields twice; future derived returns and fund fees use fractions |
| Eastmoney financial profit | `PARENT_NETPROFIT` | `net_profit`: 归母净利润, profit attributable to parent | Does not represent total corporate profit |
| Company capital | Comma-separated numbers with 万/亿 suffix | ×10000/×100000000 CNY | Bare numeric capital is parsed but its unit remains unverified |
| Fund NAV adapter | `DWJZ`, `LJJZ` | CNY/fund_unit | Cumulative NAV is the provider cumulative-value series, not reinvested total return |

Fund NAV results contain immutable rows and safe attempt metadata. Received counts measure raw dated records, while unit/cumulative values form up to two normalized observations per record; no database writes happen in these adapters. Missing one kind carries `missing_nav_value`; records with no usable values fail rather than reporting healthy empty data. Pagination is bounded to three requested pages of up to100 rows with explicit truncated or unknown coverage. The vendor can clamp100 to20; a valid PageSize echo controls short-page detection so full native pages continue within the same three-page cap. Optional PageIndex echoes must match the requested page. Duplicate dates are de-duplicated but cannot certify complete distinct-date coverage; conflicting values reject the fetch. Fund assets accept positive finite explicit 元/万/亿 currency amounts only; bare numeric assets remain unknown. Fund publication clocks stay unknown and are never set to acquisition time. Raw NAV results disclose `valuation_basis=official_nav` separately from `price_basis=unknown`; official NAV is not a market-price adjustment enum. Fund announcements are unavailable pending a verified fund-specific contract.

Financial optional fields stay `None` when absent/empty. Malformed required values are rejected by the existing parser or aggregate validation. Prices are checked before persistence. Missing source fields must never become certified zeros. Catalog conversion text describes the parser plus aggregate normalization; it does not execute conversion. Field `normalized_type` distinguishes dates, UTC datetimes, Decimal numbers, integer counts and strings. Unsupported or unknown units stay explicit even if a numeric parser succeeds.

## Time and verification

Source time and acquisition time are distinct. Daily bars and NAV use a valuation/trading date. Sina quote and Eastmoney minute bars interpret the source clock as Asia/Shanghai and convert to UTC. Eastmoney snapshots use Unix seconds or a 14-digit Shanghai clock. Tencent index times use a Shanghai clock; Sina/NetEase index timestamps are absent. Financial `NOTICE_DATE` only sorts rows and often has date-only precision; the current financial parser does not persist a publication clock. Naive news/announcement/macro timestamps are assigned UTC by current parsers, but their actual source timezone is unverified. A date assigned midnight is not proof of an exact publication time.

| Field verification | Meaning |
|---|---|
| `parser_contract` | Mapping reflects current parser implementation; does not certify real vendor units, endpoint uptime, or all instruments |
| `sample_verified` | Limited public samples support the specified field only |
| `unverified` | Units, source time, optional capability, or planned mapping remain unresolved |

Limited sample evidence: public ETF515980 volumes on 2026-09-29/30 are Sina119913400/110074800 shares versus Eastmoney1199134/1100748 lots, supporting the ×100 volume mapping for those samples. Eastmoney600519 financial samples contain revenue92278072083.21 CNY, parent profit44516880421.86 CNY, EPS35.57 CNY/share and ROE16.75%; lowercase profile `jbzl.zczb` sample `12.50亿` supports suffix conversion only. These samples do not certify an entire source, all instruments, freshness or adjustment coverage. Native NetEase percent scaling remains unknown. Public ETF515980 fund sample on 2026-10-01 reported NAV date2026-09-30 with unit0.9567 and cumulative1.9134; fund profile reported management0.50% and custody0.10% annual fees, assets72.86亿元 as of2026-06-30 and benchmark description中证人工智能产业指数收益率. These limited observations verify the corresponding units/fields only, not current source health or complete fund coverage.

Runtime acquisition success, empty/failure attempts, timestamps and quality issues are recorded independently by acquisition services. Never infer source health from a registered contract or a historical sample. Untracked homepage/lookup parsers have no managed-security attempt history.

## Managed data interfaces

| Interface | Purpose | External acquisition |
|---|---|---|
| `GET /api/data/sources` | Independent vendor contracts, effective settings and bounded actual attempt history | None |
| `GET /api/data/sources/{vendor_key}` | One vendor, including scopes outside managed security acquisition | None |
| `PUT /api/data/sources/{vendor_key}` | Change the strict boolean `enabled` setting for configurable managed vendors | None |
| `GET /api/data/securities/{security_id}` | Saved category health, source/units/date precision, metadata and bounded NAV observations | None |
| `POST /api/data/securities/{security_id}/sync` | Explicit selected-category acquisition; an optional price source applies only to price history | Requested categories only |
| `PUT /api/data/securities/{security_id}/metadata` | Manual instrument classification and market-qualified benchmark mapping | None |

Category names are `announcements`, `news`, `price_history`, `quote_snapshot`, `financial_metrics`, `company_profile`, `fund_nav` and `fund_profile`. A requested category can succeed, remain partial, be empty, fail, be disabled, or be unavailable/not applicable. Acquisition outcomes and saved dataset health are separate: a completed fetch can still leave unresolved unit or coverage issues. Source settings apply to managed acquisition, including the existing stock/watchlist sync chain; they do not control untracked homepage/search parsers.

Fund classification requires an explicit manual choice, an exact recognized lookup label, or corroborating profile evidence. A generic fund label first needs profile resolution; NAV-only actions do not silently fetch a profile. A successful unresolved profile records a classification issue and prevents implicit ETF/LOF reuse until positive evidence or an explicit manual choice resolves it. Benchmark identifiers must include their market, such as `SH:000300`; a source benchmark description alone is not a connected index dataset.

Manual overlays apply to classification and benchmark fields. Provider-derived manager, fees and dated assets retain their own provenance on subsequent profile updates. Received NAV counts refer to raw dated records; written counts refer to normalized kind observations. Coverage is bounded, and elapsed-time freshness does not claim a verified exchange calendar. Failed or disabled actions preserve prior saved records and last-success evidence.

## Extension procedure

1. Inspect the actual endpoint response and parser; record raw field paths, accepted types, units, missing rules, date precision and price basis in the owning vendor module.
2. Mark unsupported mappings `unverified`; mark future endpoint integration `planned`. Capture field-scoped sample evidence before using `sample_verified`. No instrument classification by code prefix or fabricated benchmark identifiers.
3. Implement a source adapter and focused lazy builder with request-local state. Preserve explicit provider/category keys and agreed ordering; move scope to `managed_security` only when the real acquisition chain is wired.
4. Verify native-to-normalized mapping with isolated HTTP fixtures, missing/malformed data, unknown units and provider selection. Confirm catalog reads cannot perform network/database access and returned objects are immutable.
5. Run focused and full backend regressions. Update the formal capability/field tables and validate runtime attempts separately. Metrics and research consumers must use validated normalized datasets.

## Field catalog

The following tables correspond to the source-owned catalog. Paths within row-based responses are relative to each row unless prefixed by the payload root.

### Eastmoney

#### `eastmoney` / `announcements`

Endpoint: `https://np-anotice-stock.eastmoney.com/api/security/ann`. Payload: JSON. Frequency: on_request. Scope: `managed_security`.

Time: Naive source time assigned UTC by current parser; source timezone unverified; date-only precision retained conceptually, no exact publication clock certified. Basis: not_applicable.

- At most 3 pages by default; empty codes list filtered.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| data.list[].title | string; text | title: string; text | trim | reject absent | parser_contract |
| notice_date / display_time | string; ISO date/datetime | published_at: datetime; UTC datetime | fromisoformat; naive assigned UTC | reject absent | unverified |
| art_code | string; text | url: string; text | https://data.eastmoney.com/notices/detail/{art_code}.html | None if absent | parser_contract |
| summary | string; text | summary: string; text | identity | None if absent | parser_contract |

#### `eastmoney` / `news`

Endpoint: `https://search-api-web.eastmoney.com/search/jsonp`. Payload: JSONP. Frequency: on_request. Scope: `managed_security`.

Time: Naive source time assigned UTC by current parser; source timezone unverified; date-only precision retained conceptually, no exact publication clock certified. Basis: not_applicable.

- Keyword news relevance is not semantic certification; 3 pages default.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| result.cmsArticleWebOld[].title | string; text | title: string; text | strip HTML and unescape | reject absent | parser_contract |
| date | string; YYYY-MM-DD HH:MM:SS | published_at: datetime; UTC datetime | naive assigned UTC | reject absent | unverified |
| url | string; text | url: string; text | identity | None if absent | parser_contract |
| content | string; text | summary: string; text | strip HTML and unescape | None if absent | parser_contract |

#### `eastmoney` / `price_history`

Endpoint: `https://push2his.eastmoney.com/api/qt/stock/kline/get`. Payload: JSON data.klines array of CSV strings. Frequency: daily (klt=101). Scope: `managed_security`.

Time: Trading date only; no intraday timestamp. Basis: forward_adjusted (fqt=1).

- All returned rows required valid; at most request limit, not certified inception coverage.
- Forward-adjusted close cannot be compared directly with raw fund NAV for premium.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| data.klines[][0] | string; ISO date | trade_date: date; date | date.fromisoformat | reject malformed row | parser_contract |
| data.klines[][1] | string; CNY | open_price: Decimal; CNY | Decimal | reject malformed row | parser_contract |
| data.klines[][2] | string; CNY | close_price: Decimal; CNY | Decimal | reject malformed row | parser_contract |
| data.klines[][3] | string; CNY | high_price: Decimal; CNY | Decimal | reject malformed row | parser_contract |
| data.klines[][4] | string; CNY | low_price: Decimal; CNY | Decimal | reject malformed row | parser_contract |
| data.klines[][5] | string; lots | volume: Decimal; shares | raw Decimal; aggregate multiplies by 100 | reject malformed row | sample_verified |
| data.klines[][6] | string; CNY | amount: Decimal; CNY | Decimal | reject malformed row | parser_contract |

#### `eastmoney` / `quote_snapshot`

Endpoint: `https://push2.eastmoney.com/api/qt/stock/get`. Payload: JSON. Frequency: on_request. Scope: `managed_security`.

Time: f124 source timestamp converted to UTC Basis: snapshot basis unverified.


| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| data.f43 | number / string; scaled CNY | last_price: Decimal; CNY | Decimal / 10**f59 (default precision 2) | reject absent | parser_contract |
| data.f169 | number / string; scaled CNY | change_amount: Decimal; CNY | Decimal / 10**f59 (default precision 2) | reject absent | parser_contract |
| data.f59 | number / string; decimal places | price_precision (nonpersisted scaling metadata): int; decimal places | validated integer 0..8 used for 10**precision price scale; not persisted | default 2 only if absent | parser_contract |
| data.f170 | number / string; hundredths of percentage value | change_percent: Decimal; percentage_value | Decimal / 100; 1.23 means 1.23% | reject absent | parser_contract |
| data.f124 | number / string; Unix seconds or YYYYMMDDhhmmss | snapshot_time: datetime; UTC datetime | epoch UTC; 14 digits Asia/Shanghai to UTC | reject absent/zero | parser_contract |

#### `eastmoney_intraday` / `quote_snapshot`

Endpoint: `https://push2his.eastmoney.com/api/qt/stock/kline/get`. Payload: JSON data.klines CSV; complete quote fallback. Frequency: minute (klt=1). Scope: `managed_security`.

Time: Asia/Shanghai minute to UTC; fallback f124 Basis: forward_adjusted requested (fqt=1); fallback snapshot basis unverified.

- Latest 2 bars requested; only absence of nonempty string kline rows selects complete quote fallback. Malformed selected rows raise. Previous close is never a live price.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| data.klines[-1][0] | string; YYYY-MM-DD HH:MM | snapshot_time: datetime; UTC datetime | Asia/Shanghai to UTC | reject malformed selected row; complete quote fallback only when no nonempty string kline rows | parser_contract |
| data.klines[-1][2] | string; CNY | last_price: Decimal; CNY | Decimal | reject malformed selected row; complete quote fallback only when no nonempty string kline rows | parser_contract |
| data.prePrice / preKPrice | number / string; CNY | change_amount: Decimal; CNY | latest close minus previous close; quantize 0.0001 | reject absent/zero previous close | parser_contract |
| data.prePrice / preKPrice + latest close | number / string; CNY inputs | change_percent: Decimal; percentage_value | (close-previous)/previous*100; quantize 0.0001 | reject absent/zero previous close | parser_contract |
| data.f43 | number / string; scaled CNY | last_price: Decimal; CNY | Decimal / 10**f59 (default precision 2) | reject absent | parser_contract |
| data.f169 | number / string; scaled CNY | change_amount: Decimal; CNY | Decimal / 10**f59 (default precision 2) | reject absent | parser_contract |
| data.f59 | number / string; decimal places | price_precision (nonpersisted scaling metadata): int; decimal places | validated integer 0..8 used for 10**precision price scale; not persisted | default 2 only if absent | parser_contract |
| data.f170 | number / string; hundredths of percentage value | change_percent: Decimal; percentage_value | Decimal / 100; 1.23 means 1.23% | reject absent | parser_contract |
| data.f124 | number / string; Unix seconds or YYYYMMDDhhmmss | snapshot_time: datetime; UTC datetime | epoch UTC; 14 digits Asia/Shanghai to UTC | reject absent/zero | parser_contract |

#### `eastmoney` / `financial_metrics`

Endpoint: `https://datacenter-web.eastmoney.com/api/data/v1/get`. Payload: JSON. Frequency: on_request. Scope: `managed_security`.

Time: NOTICE_DATE sorts rows; often date-only; parser does not persist publication timestamp. Basis: not_applicable.

- RPT_LICO_FN_CPD; 8 rows default; debt ratio not requested.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| result.data[].REPORT_DATE_NAME / DATATYPE | string; text | report_period: string; text | nonempty REPORT_DATE_NAME preserved verbatim; otherwise DATATYPE year 一季报/半年报/三季报/年报 -> Q1/Q2/Q3/Q4 | reject absent | parser_contract |
| TOTAL_OPERATE_INCOME | number / string; CNY | revenue: Decimal; CNY | optional Decimal | None if absent | sample_verified |
| PARENT_NETPROFIT | number / string; CNY | net_profit: Decimal; CNY | optional Decimal; 归母净利润 (profit attributable to parent), not total profit | None if absent | sample_verified |
| BASIC_EPS | number / string; CNY/share | eps: Decimal; CNY/share | optional Decimal | None if absent | sample_verified |
| WEIGHTAVG_ROE | number / string; percentage_value | roe: Decimal; percentage_value | optional Decimal; 16.75 means 16.75% | None if absent | sample_verified |
| DEBT_ASSET_RATIO | number / string; unverified | debt_to_asset_ratio: Decimal; unverified | optional Decimal; column not requested | None if absent | unverified |
| NOTICE_DATE | string; date/datetime | not persisted: string; date precision | request sorting only; no publication datetime mapping | None if absent | unverified |

#### `eastmoney` / `company_profile`

Endpoint: `https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax`. Payload: JSON. Frequency: on_request. Scope: `managed_security`.

Time: not supplied Basis: not_applicable.

- First nonempty alias wins; bare numeric capital unit remains unverified.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| jbzl.FULLNAME / gsmc | string; text | full_name: string; text | identity | None if absent | parser_contract |
| jbzl.ENAME / ywmc | string; text | english_name: string; text | identity | None if absent | parser_contract |
| jbzl.REGCAPITAL / zczb (万/亿 suffix) | string; CNY 万/亿 | registered_capital: Decimal; CNY | remove commas; 万 *10000, 亿 *100000000 | None if absent | sample_verified |
| jbzl.REGCAPITAL / zczb (bare numeric) | string; unverified | registered_capital: Decimal; unverified | Decimal identity; no unit inference | None if absent | unverified |
| jbzl.FOUNDDATE / clrq | string; ISO date | establishment_date: date; date | date.fromisoformat | None if absent | parser_contract |
| jbzl.WEBSITE / gswz | string; text | website: string; text | prepend https:// if missing scheme | None if absent | parser_contract |
| jbzl.MAINBUSINESS / zyyw / jyfw / gsjj | string; text | main_business: string; text | identity | None if absent | parser_contract |
| jbzl.EMPNUM / ygs / gyrs | string; persons text | employees: int; persons | extract digits; int | None if absent | parser_contract |

#### `eastmoney` / `lookup`

Endpoint: `https://searchapi.eastmoney.com/api/suggest/get`. Payload: JSON. Frequency: on_request. Scope: `untracked_homepage/lookup`.

Time: not supplied Basis: not_applicable.

- Exact code/market match required; labels do not infer fund type from code prefix.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| QuotationCodeTable.Data[].Code | string; text | code: string; text | identity | lookup requires exact match; search skips absent | parser_contract |
| QuotationCodeTable.Data[].Name | string; text | name: string; text | identity | reject absent | parser_contract |
| QuotationCodeTable.Data[].MktNum | string; text | market: string; text | 1/SH -> SH; 0/2/SZ -> SZ | unsupported rows skipped by search; lookup rejects mismatch | parser_contract |
| QuotationCodeTable.Data[].SecurityTypeName | string; text | industry: string; text | classification label; not actual business industry | None if absent | parser_contract |

#### `eastmoney` / `search`

Endpoint: `https://searchapi.eastmoney.com/api/suggest/get`. Payload: JSON. Frequency: on_request. Scope: `untracked_homepage/lookup`.

Time: not supplied Basis: not_applicable.

- SH/SZ only; de-duplicate market/code; 20 results default.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| QuotationCodeTable.Data[].Code | string; text | code: string; text | identity | lookup requires exact match; search skips absent | parser_contract |
| QuotationCodeTable.Data[].Name | string; text | name: string; text | identity | reject absent | parser_contract |
| QuotationCodeTable.Data[].MktNum | string; text | market: string; text | 1/SH -> SH; 0/2/SZ -> SZ | unsupported rows skipped by search; lookup rejects mismatch | parser_contract |
| QuotationCodeTable.Data[].SecurityTypeName | string; text | industry: string; text | classification label; not actual business industry | None if absent | parser_contract |

#### `eastmoney` / `market_index`

Endpoint: `https://push2.eastmoney.com/api/qt/stock/get`. Payload: JSON. Frequency: on_request. Scope: `untracked_homepage/lookup`.

Time: f124 epoch UTC or absent Basis: not_applicable.


| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| data.f58 | string; text | name: string; text | identity | static index name fallback | parser_contract |
| data.f43 | number / string; hundredths of index point | last_value: Decimal; index_points | Decimal /100 | None if absent | parser_contract |
| data.f169 | number / string; hundredths of index point | change_amount: Decimal; index_points | Decimal /100 | None if absent | parser_contract |
| data.f170 | number / string; hundredths of percentage value | change_percent: Decimal; percentage_value | Decimal /100 | None if absent | parser_contract |
| data.f124 | number / string; Unix seconds | snapshot_time: datetime; UTC datetime | fromtimestamp UTC | None if absent/zero | parser_contract |

#### `eastmoney` / `macro`

Endpoint: `https://datacenter-web.eastmoney.com/api/data/v1/get`. Payload: JSON. Frequency: on_request. Scope: `untracked_homepage/lookup`.

Time: Naive source time assigned UTC by current parser; source timezone unverified; date-only precision retained conceptually, no exact publication clock certified. Basis: not_applicable.

- Latest row per CPI/PPI/PMI/M2; report period is not exact publication clock.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| NATIONAL_SAME / BASE_SAME / CURRENCY_SAME | number / string; percentage_value | value: string; percentage_value | string; CPI/PPI/M2 selected by report | None if absent | parser_contract |
| MAKE_INDEX | number / string; index_points | value: string; index_points | string; manufacturing PMI | None if absent | parser_contract |
| NATIONAL_SEQUENTIAL / BASE_ACCUMULATE / MAKE_SAME / CURRENCY_SEQUENTIAL | number / string; percentage_value | change_text: string; display text | prefix label and append % | None if absent | parser_contract |
| REPORT_DATE | string; ISO date/datetime | published_at: datetime; UTC datetime | naive assigned UTC | None if absent | unverified |
| TIME | string; text | summary: string; text | identity | None if absent | parser_contract |

#### `eastmoney_fund_nav` / `fund_nav`

Endpoint: `https://api.fund.eastmoney.com/f10/lsjz`. Payload: JSON Data.LSJZList array of objects. Frequency: daily. Scope: `managed_security`.

Time: NAV valuation date only; publication clock unknown. Basis: unknown market-price basis; separate official_nav valuation basis.

- Managed explicit/corroborated ETF/LOF acquisition; generic 基金 profile resolution does not authorize NAV until positive type evidence.
- At most 3 requested pages of up to 100 raw NAV date rows; native PageSize can clamp to 20. Validated native size controls short-page detection while the 3-page cap remains fixed; truncated/unknown coverage explicit. Raw received counts differ from normalized unit/cumulative observations and later writes.
- Conflicting duplicates or any malformed page reject entire fetch; no partial healthy result.
- Cumulative NAV is provider cumulative-value series, not reinvested total return. Forward-adjusted prices cannot establish premium.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| Data.LSJZList[].FSRQ | string; ISO date | nav_date: date; date | strict date.fromisoformat; sort dates | reject absent or malformed | parser_contract |
| Data.LSJZList[].DWJZ | string / number; CNY/fund_unit | unit_nav: Decimal; CNY/fund_unit | positive finite Decimal; FundNavRow kind unit_nav | None/empty/-- omitted and missing_nav_value flagged; all unusable rejects fetch | sample_verified |
| Data.LSJZList[].LJJZ | string / number; CNY/fund_unit | cumulative_nav: Decimal; CNY/fund_unit | positive finite Decimal; FundNavRow kind cumulative_nav | None/empty/-- omitted and missing_nav_value flagged; all unusable rejects fetch | sample_verified |
| PageSize | number / string; native page record limit | effective_page_size (validation only): int | positive integral <= requested size; rows <= echo; native short-page detection | requested size if absent; invalid supplied echo rejects whole fetch | parser_contract |
| PageIndex | number / string; page number | page_index (validation only): int | positive integral equals requested pageIndex | no corroboration if absent; invalid supplied echo rejects whole fetch | parser_contract |
| TotalCount | number / string; raw NAV date records | total_count: int; raw NAV date records | nonnegative integral count | unknown coverage if absent | parser_contract |
| absent publication clock | string; unknown | published_at: datetime; unknown | None; acquisition time never substitutes | None if absent | unverified |

#### `eastmoney_fund_profile` / `fund_profile`

Endpoint: `https://fundf10.eastmoney.com/jbgk_{code}.html`. Payload: HTML table label/value cells and recognized fund title. Optional HTML cell and row end tags are supported, including the public profile page’s omitted `</td>` before the next `<th>`. Frequency: on_request. Scope: `managed_security`.

Time: Asset valuation date only if supplied; publication clock unknown. Basis: not_applicable.

- Managed explicit/corroborated ETF/LOF acquisition; generic 基金 profile resolution does not authorize NAV until positive type evidence.
- No invented benchmark code or prefix-based fund classification; identity-only pages with no usable metadata reject fetch.
- Fund announcements unavailable: stock-company announcements are not a fund-data substitute; no guessed endpoint.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| recognized fund title / 基金代码 / 基金主代码 | string; text | code (validation only): string; text | corroborate requested six-digit code; scripts excluded | reject absent/mismatch | parser_contract |
| 基金全称 | string; text | full_name: string; text | HTML text/entity normalization | None if absent | sample_verified |
| 基金全称 explicit ETF/交易型开放式/LOF/上市开放式 | string; text | instrument_type: string; text | explicit full-name marker only; 联接/feeder excludes ETF inference, retain unknown unless independent LOF marker; no numeric prefix inference | unknown if no marker | parser_contract |
| 基金管理人 | string; text | manager: string; text | HTML text/entity normalization; not fund custodian | None if absent | sample_verified |
| 业绩比较基准 | string; text | benchmark_name: string; text | preserve description; no inferred benchmark code | None if absent | sample_verified |
| 管理费率 | string; annual percentage text | management_fee: Decimal; fraction | finite percentage /100; 0..1 | None/empty/-- absent; malformed rejects fetch | sample_verified |
| 托管费率 | string; annual percentage text | custody_fee: Decimal; fraction | finite percentage /100; 0..1 | None/empty/-- absent; malformed rejects fetch | sample_verified |
| 净资产规模 / 资产规模 explicit 万/亿/元 | string; CNY suffix text | fund_assets: Decimal; CNY | positive finite Decimal times 10000/100000000/1 | None if absent or bare unitless number; malformed explicit amount rejects fetch | sample_verified |
| 净资产规模 / 资产规模 截止至 / 截止日期 | string; YYYY年MM月DD日 / YYYY-MM-DD | assets_as_of: date; date | calendar date; no publication time inferred | None if absent; invalid date rejects fetch | sample_verified |

### Sina

#### `sina` / `announcements`

Endpoint: `https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllBulletin/stockid/{stock_code}.phtml`. Payload: HTML. Frequency: on_request. Scope: `managed_security`.

Time: Current parser assigns UTC to naive values; source timezone unverified; date-only has no exact publication clock. Basis: not_applicable.


| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| div.datelist a text | string; text | title: string; text | join stripped text | reject missing rows/title | parser_contract |
| div.datelist date text | string; ISO date/datetime | published_at: datetime; UTC datetime | slashes to hyphens; naive assigned UTC | reject absent | unverified |
| a href | string; text | url: string; text | urljoin Sina origin | None if absent | parser_contract |

#### `sina` / `news`

Endpoint: `https://finance.sina.com.cn/stock/api/jsonp.php/var%20news=/StockNewsService.getNewsList`. Payload: JSON object result.data[] or data[] (response.json parser; no JSONP decoding). Frequency: on_request. Scope: `managed_security`.

Time: Current parser assigns UTC to naive values; source timezone unverified; date-only has no exact publication clock. Basis: not_applicable.

- URL resembles JSONP but parser expects JSON dict; live compatibility unverified.
- 3 pages default; keyword results are not relevance certification.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| result.data[] / data[].title | string; text | title: string; text | identity | reject absent | parser_contract |
| result.data[] / data[].ctime | string; YYYY-MM-DD HH:MM:SS | published_at: datetime; UTC datetime | naive assigned UTC | reject absent | unverified |
| result.data[] / data[].url | string; text | url: string; text | urljoin Sina origin | reject absent | parser_contract |
| result.data[] / data[].intro | string; text | summary: string; text | identity | None if absent | parser_contract |

#### `sina` / `price_history`

Endpoint: `https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData`. Payload: JSON array. Frequency: daily scale=240. Scope: `managed_security`.

Time: Trading date only Basis: unknown.

- Maximum 5000 bars/request; not full-history certification.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| day | string; ISO date | trade_date: date; date | date.fromisoformat | reject absent | parser_contract |
| open | number / string; CNY | open_price: Decimal; CNY | Decimal | reject absent/malformed | parser_contract |
| high | number / string; CNY | high_price: Decimal; CNY | Decimal | reject absent/malformed | parser_contract |
| low | number / string; CNY | low_price: Decimal; CNY | Decimal | reject absent/malformed | parser_contract |
| close | number / string; CNY | close_price: Decimal; CNY | Decimal | reject absent/malformed | parser_contract |
| volume | number / string; shares | volume: Decimal; shares | Decimal identity | reject absent | sample_verified |
| (absent) | string; unavailable | amount: Decimal; unavailable | legacy non-null model stores 0; metadata amount_available=False | unavailable, never a measured zero | unverified |

#### `sina_fund` / `quote_snapshot`

Endpoint: `https://hq.sinajs.cn/list={market}{code}`. Payload: JavaScript assignment of CSV string. Frequency: on_request. Scope: `managed_security`.

Time: Source date/time Asia/Shanghai to UTC Basis: snapshot basis unverified.

- Name is legacy provider key; no code-prefix fund classification.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| CSV[3] | string; CNY | last_price: Decimal; CNY | Decimal | reject absent | parser_contract |
| CSV[2],CSV[3] | string; CNY | change_amount: Decimal; CNY | last - previous; quantize 0.0001 | reject zero previous close | parser_contract |
| CSV[2],CSV[3] | string; CNY inputs | change_percent: Decimal; percentage_value | (last-previous)/previous*100; quantize 0.0001 | reject zero previous close | parser_contract |
| CSV[30],CSV[31] | string; Shanghai date/time | snapshot_time: datetime; UTC datetime | Asia/Shanghai to UTC | reject absent/malformed | parser_contract |

#### `sina` / `market_index`

Endpoint: `https://hq.sinajs.cn/list={symbols}`. Payload: JavaScript assignment of simplified s_ CSV. Frequency: on_request. Scope: `untracked_homepage/lookup`.

Time: not supplied Basis: not_applicable.

- No source timestamp; volume/amount fields unused.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| CSV[0] | string; text | name: string; text | identity | static name fallback | parser_contract |
| CSV[1] | string; index_points | last_value: Decimal; index_points | Decimal | skip missing/nonpositive | parser_contract |
| CSV[2] | string; index_points | change_amount: Decimal; index_points | Decimal | None if absent | parser_contract |
| CSV[3] | string; percentage_value | change_percent: Decimal; percentage_value | Decimal identity | None if absent | parser_contract |

### NetEase

#### `netease` / `price_history`

Endpoint: `https://api.money.126.net/data/history/{symbol}/day.json`. Payload: JSON data array of arrays. Frequency: daily; 500 rows/page. Scope: `managed_security`.

Time: Trading date only Basis: unknown.

- Volume unit and amount availability unverified; aggregate cannot certify shares or adjustment.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| data[][0] | string; date | trade_date: date; date | slashes to hyphens; date.fromisoformat | reject absent/malformed | parser_contract |
| data[][1] | number / string; unverified | open_price: Decimal; unverified | Decimal identity | reject absent/malformed | unverified |
| data[][2] | number / string; unverified | high_price: Decimal; unverified | Decimal identity | reject absent/malformed | unverified |
| data[][3] | number / string; unverified | low_price: Decimal; unverified | Decimal identity | reject absent/malformed | unverified |
| data[][4] | number / string; unverified | close_price: Decimal; unverified | Decimal identity | reject absent/malformed | unverified |
| data[][5] | number / string; unverified | volume: Decimal; unverified | Decimal identity | reject absent/malformed | unverified |
| data[][6] | number / string; unverified | amount: Decimal; unverified | Decimal identity | reject absent/malformed | unverified |

#### `netease` / `market_index`

Endpoint: `https://api.money.126.net/data/feed/{symbol}`. Payload: JSONP _ntes_quote_callback. Frequency: on_request. Scope: `untracked_homepage/lookup`.

Time: not supplied Basis: not_applicable.

- No timestamp; exceptions can omit an index. Native percent unit unverified. Not in current default homepage chain.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| {symbol}.name | string; text | name: string; text | identity | static name fallback | parser_contract |
| {symbol}.price | string; index_points | last_value: Decimal; index_points | Decimal | None if absent | parser_contract |
| {symbol}.updown | string; index_points | change_amount: Decimal; index_points | Decimal | None if absent | parser_contract |
| {symbol}.percent | string; unverified | change_percent: Decimal; unverified | Decimal identity; no percent/fraction scaling inferred | None if absent | unverified |

### Tencent

#### `tencent` / `market_index`

Endpoint: `https://qt.gtimg.cn/q={symbols}`. Payload: JavaScript assignments of tilde-delimited strings. Frequency: on_request. Scope: `untracked_homepage/lookup`.

Time: Asia/Shanghai source clock -> UTC Basis: not_applicable.

- No managed-security price-history fetch adapter; isolated unused kline parser is not an endpoint.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| parts[1] | string; text | name: string; text | identity | static name fallback | parser_contract |
| parts[3] | string; index_points | last_value: Decimal; index_points | Decimal | skip missing/nonpositive | parser_contract |
| parts[31] | string; index_points | change_amount: Decimal; index_points | Decimal | None if absent | parser_contract |
| parts[32] | string; percentage_value | change_percent: Decimal; percentage_value | Decimal identity | None if absent | parser_contract |
| parts[30] | string; YYYYMMDDhhmmss | snapshot_time: datetime; UTC datetime | Asia/Shanghai to UTC | None if invalid | parser_contract |

### Ifeng

#### `ifeng` / `news`

Endpoint: `https://finance.ifeng.com/app/hq/stock/{market}{stock_code}/news`. Payload: HTML. Frequency: on_request. Scope: `planned`.

Time: Naive source timezone unverified; parser assigns UTC. Basis: not_applicable.

- Existing parser only; not wired into default stock sync or homepage. Planned integration does not mean parser missing.

| Native field | Native type/unit | Target type/unit | Conversion | Missing rule | Verification |
|---|---|---|---|---|---|
| article.news-item a text | string; text | title: string; text | join stripped text | reject missing rows/title | parser_contract |
| time datetime / text | string; ISO datetime | published_at: datetime; UTC datetime | naive assigned UTC; aware converted UTC | reject absent | unverified |
| a href | string; text | url: string; text | urljoin Ifeng origin | None if absent | parser_contract |
| p text | string; text | summary: string; text | join stripped text | None if absent | parser_contract |

## Managed security data center

`GET /api/data/securities/{id}` reads bounded local acquisition/quality evidence without provider calls. `POST /api/data/securities/{id}/sync` accepts strict category subsets and an optional explicit daily-price source. The default history order prefers the dataset's last successful known-basis source, then Eastmoney forward-adjusted prices before unknown-basis fallbacks. Disabled vendors/aliases perform no acquisition and preserve last-good records. An explicit history-source choice requires a matching selectable source-owned adapter; an opaque custom provider returns unavailable without acquisition, while default custom-provider compatibility remains. A failed retry is distinct from retained observation/acquisition freshness.

Fund NAV/profile are managed only for manual ETF/LOF, exact positive security-type labels, or code-corroborated profile subtype evidence. Generic 基金 can resolve through a requested profile; NAV-only requests never hide a profile lookup. Stock/index/unknown classifications never query same-number off-exchange fund data. No code-prefix or display-name inference is used. General news uses the existing actual providers; fund announcements remain unavailable without a verified contract.

NAV values remain exact decimal strings with separate unit/cumulative kinds, real valuation dates, unknown publication clocks, raw-date received counters and kind-observation written counters. Limited/missing coverage carries unresolved quality issues. Metadata preserves omitted provider fields; a new asset amount without a supplied valuation date clears that date rather than reusing an old date. A first benchmark-only manual overlay snapshots the current effective classification, including unknown after an unresolved profile, rather than reviving a historical provider type. Existing explicit manual classification remains unchanged by later benchmark-only edits. Manual type and market-qualified benchmark overlays survive acquisition and apply only to those fields, while fees/assets/manager disclose fund-profile provenance.

Health states distinguish healthy/stale/partial/failed/unknown/not_applicable. Age thresholds are elapsed-time estimates (daily series 7 days, quotes 3, news 30, announcements 90, financial/fund metadata 180, company profile 365); no verified exchange/fund calendar or latest-session guarantee exists. Publication/effective-asof dates are never invented from fetch time.

### Resolved index context

Only an explicit resolved index classification (exact recognized label or manual index override) activates contextual normalization. Eastmoney source-owned contracts declare daily and quote/minute index levels as `index_points`; numeric prices are unchanged. Unsupported or opaque contexts retain unknown units and `unit_unverified` quality evidence. Stock/ETF currency and source ordering remain unchanged. This instrument context is classification evidence, not vendor verification of every field.

Index corporate adjustment remains `unknown` with explicit quality evidence. Index component volume is not certified as per-security share volume: fresh request-local raw adapters suppress equity lot-to-share conversion, preserve native numeric volume and mark its units/comparability unverified. No retained rows are migrated, reverse-scaled or rewritten by merely reading or changing classification; actual requested refreshes still obey existing whole-series integrity guards.

Read-only index views conservatively disclose legacy CNY units/equity adjustment labels as unknown unless new acquisition records carry the source-owned index-point context. These are derived read disclosures, with no persisted issues or database mutations fabricated by GET. Acquisition/observation dates and their disclosed precision remain unchanged.
