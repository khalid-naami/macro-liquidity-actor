import datetime
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def determine_macro_regime(gdp_growth: float, cpi_inflation: float) -> tuple:
    """Determine Macro Business Cycle Quadrant."""
    if gdp_growth >= 2.0 and cpi_inflation <= 3.0:
        return "Disinflationary Boom (Goldilocks) 🌟", "Strong growth with moderate price stability. Favorable for high-beta equities & tech."
    elif gdp_growth >= 2.0 and cpi_inflation > 3.0:
        return "Reflationary Expansion 🔥", "Above-trend economic expansion accompanied by rising price pressures. Benefits commodities & cyclicals."
    elif gdp_growth < 2.0 and cpi_inflation > 3.0:
        return "Stagflationary Pressure ⚠️", "Sub-trend growth coupled with stubborn inflation. Highly challenging for multiples; favors cash & real assets."
    else:
        return "Contraction / Deflationary Slowdown ❄️", "Slowing growth and rapidly decelerating inflation. Drives central bank rate cuts and sovereign bond rallies."

def calculate_liquidity_metrics(df_liq: pd.DataFrame) -> dict:
    """Calculate Net Liquidity indicators and historical deltas."""
    if df_liq.empty:
        return {}
        
    latest = df_liq.iloc[-1]
    prev_1w = df_liq.iloc[-2] if len(df_liq) >= 2 else latest
    prev_1m = df_liq.iloc[-5] if len(df_liq) >= 5 else df_liq.iloc[0]
    prev_1y = df_liq.iloc[-52] if len(df_liq) >= 52 else df_liq.iloc[0]
    
    net_now = float(latest['Net_Liquidity'])
    delta_1w = round(float(net_now - prev_1w['Net_Liquidity']), 2)
    delta_1m = round(float(net_now - prev_1m['Net_Liquidity']), 2)
    delta_1y = round(float(net_now - prev_1y['Net_Liquidity']), 2)
    
    return {
        "asOfDate": latest['Date'].strftime('%Y-%m-%d'),
        "totalAssetsBillions": round(float(latest['Total_Assets']), 2),
        "reverseRepoBillions": round(float(latest['Reverse_Repo']), 2),
        "treasuryAccountBillions": round(float(latest['TGA']), 2),
        "netLiquidityBillions": round(net_now, 2),
        "netLiquidityWeeklyDeltaBillions": delta_1w,
        "netLiquidityMonthlyDeltaBillions": delta_1m,
        "netLiquidityYearlyDeltaBillions": delta_1y,
        "policyRegime": "Quantitative Tightening (QT)" if delta_1m < 0 else "Liquidity Expansion (QE / Neutral)"
    }

def calculate_asset_correlations(df_liq: pd.DataFrame, asset_dict: dict) -> dict:
    """
    Align Wednesday Net Liquidity dates with risk asset close prices and compute Pearson correlations.
    """
    results = {}
    
    for ticker, series in asset_dict.items():
        if series.empty:
            continue
            
        df_asset = pd.DataFrame({'Date': series.index, 'Asset_Price': series.values})
        # Merge on exact Date
        merged = pd.merge(df_liq[['Date', 'Net_Liquidity', 'Total_Assets', 'TGA', 'Reverse_Repo']], df_asset, on='Date', how='inner')
        
        if len(merged) < 10:
            # Fallback: Merge nearest date within 3 days
            merged = pd.merge_asof(
                df_liq[['Date', 'Net_Liquidity', 'Total_Assets', 'TGA', 'Reverse_Repo']].sort_values('Date'),
                df_asset.sort_values('Date'),
                on='Date',
                direction='nearest',
                tolerance=pd.Timedelta(days=3)
            ).dropna(subset=['Asset_Price'])
            
        if len(merged) >= 10:
            r = float(merged['Net_Liquidity'].corr(merged['Asset_Price']))
            r_rounded = round(r, 4)
            
            # Classification
            if r_rounded >= 0.70:
                desc = "Strong Positive Coupling (Price heavily driven by Fed Liquidity)"
            elif r_rounded >= 0.35:
                desc = "Moderate Positive Correlation"
            elif r_rounded >= -0.35:
                desc = "Neutral / Idiosyncratic Asset Drivers"
            else:
                desc = "Inverse / Counter-Cyclical Relationship"
                
            series_records = []
            for _, row in merged.tail(156).iterrows():  # last 3 years of weekly Wednesdays
                series_records.append({
                    "date": row['Date'].strftime('%Y-%m-%d'),
                    "netLiquidityBillions": round(float(row['Net_Liquidity']), 2),
                    "assetPrice": round(float(row['Asset_Price']), 2)
                })
                
            results[ticker] = {
                "rCoefficient": r_rounded,
                "relationship": desc,
                "dataPointsAligned": len(merged),
                "latestAssetPrice": round(float(merged['Asset_Price'].iloc[-1]), 2),
                "weeklySeries": series_records
            }
            
    return results

def calculate_gdp_cpi_simulation(df_cpi: pd.DataFrame, df_gdp: pd.DataFrame, assumed_mom_pct: float = 0.20) -> dict:
    """
    Calculate Real GDP, CPI Inflation, and 12-Month forward CPI trajectory simulation.
    """
    cpi_latest = df_cpi.iloc[-1]
    gdp_latest = df_gdp.iloc[-1]
    
    current_gdp_growth = round(float(gdp_latest.get('GDP_Growth_YoY', 2.5)), 2)
    current_cpi_inflation = round(float(cpi_latest.get('Inflation_YoY', 2.8)), 2)
    current_cpi_mom = round(float(cpi_latest.get('CPI_MoM', 0.2)), 2)
    
    regime_name, regime_desc = determine_macro_regime(current_gdp_growth, current_cpi_inflation)
    
    # Run 12-month forward CPI Simulation
    last_cpi_index = float(cpi_latest['CPI'])
    last_cpi_date = cpi_latest['Date']
    
    sim_dates = pd.date_range(start=last_cpi_date + pd.DateOffset(months=1), periods=12, freq='MS')
    
    sim_cpi_indices = []
    curr_sim_idx = last_cpi_index
    for _ in range(12):
        curr_sim_idx *= (1.0 + (assumed_mom_pct / 100.0))
        sim_cpi_indices.append(curr_sim_idx)
        
    # Compute simulated YoY inflation using 12-month lookback
    sim_results = []
    target_reentry_date = "Above Target (> 2.0%)"
    reentry_found = False
    
    for i, (dt, sim_val) in enumerate(zip(sim_dates, sim_cpi_indices)):
        # Look back 12 months in historical series
        past_dt = dt - pd.DateOffset(years=1)
        sub_past = df_cpi[df_cpi['Date'] <= past_dt]
        past_cpi_val = sub_past['CPI'].iloc[-1] if not sub_past.empty else last_cpi_index
        
        sim_yoy = round(float(((sim_val - past_cpi_val) / past_cpi_val) * 100.0), 2)
        
        if sim_yoy <= 2.05 and not reentry_found:
            target_reentry_date = dt.strftime('%B %Y')
            reentry_found = True
            
        sim_results.append({
            "month": dt.strftime('%Y-%m'),
            "simulatedCPIIndex": round(float(sim_val), 2),
            "projectedYoYInflationPct": sim_yoy
        })
        
    return {
        "asOfDate": last_cpi_date.strftime('%Y-%m-%d'),
        "realGdpGrowthYoY": current_gdp_growth,
        "cpiInflationYoY": current_cpi_inflation,
        "cpiInflationMoM": current_cpi_mom,
        "macroEconomicRegime": regime_name,
        "regimeDescription": regime_desc,
        "assumedMoMChangePct": assumed_mom_pct,
        "estimated2PctTargetReentry": target_reentry_date,
        "forward12MonthTrajectory": sim_results
    }

def process_g20_macro_table(indicators_raw: dict) -> list:
    """Format G20 multi-country macroeconomic indicators table."""
    g20_list = [
        "USA", "CHN", "JPN", "DEU", "GBR", "FRA", "IND", "ITA", "BRA", "CAN", 
        "RUS", "KOR", "AUS", "MEX", "IDN", "SAU", "TUR", "ARG", "ZAF"
    ]
    
    country_records = []
    for iso in g20_list:
        c_data = indicators_raw.get(iso, {})
        if not c_data:
            continue
            
        name = c_data.get("name", iso)
        data = c_data.get("data", {})
        
        # Extract latest values
        gdp_usd = next(iter(data.get("gdp_usd", {}).values()), None)
        gdp_growth = next(iter(data.get("gdp_growth", {}).values()), None)
        inflation = next(iter(data.get("inflation", {}).values()), None)
        unemp = next(iter(data.get("unemployment", {}).values()), None)
        debt = next(iter(data.get("debt_to_gdp", {}).values()), None)
        
        country_records.append({
            "iso3": iso,
            "countryName": name,
            "gdpBillionsUSD": round(float(gdp_usd) / 1e9, 2) if gdp_usd else None,
            "gdpGrowthYoYPct": round(float(gdp_growth), 2) if gdp_growth else None,
            "inflationYoYPct": round(float(inflation), 2) if inflation else None,
            "unemploymentPct": round(float(unemp), 2) if unemp else None,
            "debtToGdpPct": round(float(debt), 2) if debt else None
        })
        
    country_records.sort(key=lambda x: x["gdpBillionsUSD"] or 0, reverse=True)
    return country_records
