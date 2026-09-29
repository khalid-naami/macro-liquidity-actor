# Global Macro Liquidity & Fed Balance Sheet Intelligence 🌊🏛️

**Global Macro Liquidity & Fed Balance Sheet Intelligence** is a quantitative macroeconomics Actor on Apify. It extracts Federal Reserve balance sheet components, models weekly Wednesday **Net Banking Liquidity** ($\text{WALCL} - \text{RRP} - \text{TGA}$), calculates live Pearson statistical correlation overlays with major risk assets (**SPY, QQQ, BTC, ETH, GLD**), models US Real GDP & CPI economic cycle regimes, projects 12-month forward inflation paths, and formats multi-country G20 macroeconomic rankings.

---

## 🌟 Key Features

1. **Federal Reserve Net Liquidity Model ($\text{WALCL} - \text{RRP} - \text{TGA}$):**
   - **Total Assets (`WALCL`):** Fed balance sheet size in Billions ($B).
   - **Overnight Reverse Repo (`WLRRAL` / RRP):** Cash locked up at the Fed.
   - **Treasury General Account (`WDTGAL` / TGA):** US government cash buffer.
   - **Net Banking Liquidity:** Active reserves flowing through global financial markets with 1W, 1M, and 1Y momentum deltas.

2. **Risk Asset Historical Overlay & Pearson Correlation ($R$):**
   - Weekly Wednesday close price alignment across:
     - **SPY** (S&P 500 ETF)
     - **QQQ** (Invesco QQQ Trust)
     - **BTC-USD** (Bitcoin)
     - **ETH-USD** (Ethereum)
     - **GLD** (SPDR Gold Shares)
   - Live Pearson correlation coefficients ($R$) and classification (Coupling vs Decoupling).

3. **US Real GDP Growth & CPI Inflation Engine:**
   - Real GDP YoY Growth (`GDPC1`) and CPI YoY Inflation (`CPIAUCSL`) tracking.
   - Automatic Macro Business Cycle determination: `Disinflationary Boom (Goldilocks)`, `Reflationary Expansion`, `Stagflationary Pressure`, or `Deflationary Contraction`.

4. **12-Month Forward CPI Inflation Simulator:**
   - Interactive simulation calculating monthly YoY CPI trajectories based on assumed MoM rates and projecting estimated 2.0% Fed target re-entry dates.

5. **G20 Global Macroeconomic Rankings:**
   - Multi-country GDP, inflation, unemployment, and debt-to-GDP metrics across all G20 nations.

---

## 📥 Input Configuration

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `overlayAssets` | `array` | `["SPY", "QQQ", "BTC-USD", "ETH-USD", "GLD"]` | Assets to align on Wednesday liquidity dates and compute correlation. |
| `timeHorizonDays` | `integer` | `1095` | Days of history for overlay and correlation analysis (3Y = 1095). |
| `includeGdpCpiAnalysis` | `boolean` | `true` | Include Real GDP, CPI Inflation, and regime classifications. |
| `cpiSimulationMomPct` | `number` | `0.20` | Assumed monthly MoM rate for forward inflation simulation (%). |
| `includeHistoricalLiquiditySeries` | `boolean` | `true` | Output weekly historical Net Liquidity time series. |
| `includeG20Indicators` | `boolean` | `true` | Include multi-country G20 macroeconomic database. |

---

## 📤 Output Schema

```json
{
  "recordType": "MACRO_LIQUIDITY_DOSSIER",
  "asOfDate": "2026-09-24",
  "totalAssetsBillions": 6845.2,
  "reverseRepoBillions": 235.4,
  "treasuryAccountBillions": 718.5,
  "netLiquidityBillions": 5891.3,
  "netLiquidityWeeklyDeltaBillions": -12.4,
  "netLiquidityMonthlyDeltaBillions": -42.8,
  "policyRegime": "Quantitative Tightening (QT)",
  "spyCorrelationR": 0.8842,
  "btcCorrelationR": 0.8215,
  "qqqCorrelationR": 0.8654,
  "gldCorrelationR": -0.3210,
  "realGdpGrowthYoY": 2.5,
  "cpiInflationYoY": 2.8,
  "macroEconomicRegime": "Disinflationary Boom (Goldilocks) 🌟",
  "fedTargetReentryDate": "November 2026",
  "assetCorrelations": { ... },
  "gdpCpiAnalysis": { ... },
  "g20Rankings": [ ... ]
}
```

---

## 🚀 Local Run

```bash
uv run --with apify --with pandas --with numpy --with yfinance --with requests --with pytz --with python-dateutil python -m src.main
```
