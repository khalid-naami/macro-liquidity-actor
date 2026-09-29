import asyncio
import datetime
import logging
import pandas as pd
from apify import Actor
from src.data_engine import (
    fetch_fed_liquidity_data,
    fetch_gdp_cpi_history,
    fetch_asset_prices_series,
    load_g20_macro_indicators
)
from src.macro_engine import (
    calculate_liquidity_metrics,
    calculate_asset_correlations,
    calculate_gdp_cpi_simulation,
    process_g20_macro_table
)

logger = logging.getLogger(__name__)

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        
        overlay_assets = actor_input.get("overlayAssets", ["SPY", "QQQ", "BTC-USD", "ETH-USD", "GLD"])
        time_horizon_days = int(actor_input.get("timeHorizonDays", 1095))
        include_gdp_cpi = bool(actor_input.get("includeGdpCpiAnalysis", True))
        cpi_mom_sim = float(actor_input.get("cpiSimulationMomPct", 0.20))
        include_ts = bool(actor_input.get("includeHistoricalLiquiditySeries", True))
        include_g20 = bool(actor_input.get("includeG20Indicators", True))
        
        Actor.log.info("🌊 Starting Global Macro Liquidity & Fed Balance Sheet Intelligence Actor...")
        Actor.log.info(f"Overlay Assets: {overlay_assets} | Horizon: {time_horizon_days}D | CPI MoM Sim: {cpi_mom_sim}%")
        
        # 1. Fetch Fed Balance Sheet & Net Liquidity Data
        Actor.log.info("Fetching Federal Reserve Net Liquidity components (WALCL, RRP, TGA)...")
        df_liq = fetch_fed_liquidity_data()
        
        # 2. Filter Liquidity to timeframe
        cutoff_date = datetime.date.today() - datetime.timedelta(days=time_horizon_days)
        df_liq_filtered = df_liq[df_liq['Date'] >= pd.to_datetime(cutoff_date)].copy()
        if df_liq_filtered.empty:
            df_liq_filtered = df_liq.copy()
            
        start_str = df_liq_filtered['Date'].min().strftime('%Y-%m-%d')
        end_str = df_liq_filtered['Date'].max().strftime('%Y-%m-%d')
        
        # 3. Fetch Asset Price Histories
        Actor.log.info(f"Fetching historical price series for overlay assets {overlay_assets}...")
        asset_prices = fetch_asset_prices_series(overlay_assets, start_str, end_str)
        
        # 4. Calculate Net Liquidity Overview & Deltas
        liq_metrics = calculate_liquidity_metrics(df_liq)
        
        # 5. Calculate Weekly Asset Correlations
        Actor.log.info("Computing Wednesday close price alignment & Pearson correlation coefficients...")
        correlations = calculate_asset_correlations(df_liq_filtered, asset_prices)
        
        # 6. Calculate GDP & CPI Cycles
        gdp_cpi_results = {}
        if include_gdp_cpi:
            Actor.log.info("Analyzing US Real GDP, CPI Inflation, and forward 12M trajectory...")
            df_cpi, df_gdp = fetch_gdp_cpi_history()
            gdp_cpi_results = calculate_gdp_cpi_simulation(df_cpi, df_gdp, cpi_mom_sim)
            
        # 7. Load G20 Macro Indicators
        g20_data = []
        if include_g20:
            Actor.log.info("Processing G20 global macroeconomic indicators...")
            raw_g20 = load_g20_macro_indicators()
            if raw_g20:
                g20_data = process_g20_macro_table(raw_g20)
                
        # Build Master Record
        spy_r = correlations.get("SPY", {}).get("rCoefficient")
        btc_r = correlations.get("BTC-USD", {}).get("rCoefficient")
        qqq_r = correlations.get("QQQ", {}).get("rCoefficient")
        gld_r = correlations.get("GLD", {}).get("rCoefficient")
        
        master_record = {
            "recordType": "MACRO_LIQUIDITY_DOSSIER",
            "asOfDate": liq_metrics.get("asOfDate", datetime.date.today().strftime('%Y-%m-%d')),
            "totalAssetsBillions": liq_metrics.get("totalAssetsBillions"),
            "reverseRepoBillions": liq_metrics.get("reverseRepoBillions"),
            "treasuryAccountBillions": liq_metrics.get("treasuryAccountBillions"),
            "netLiquidityBillions": liq_metrics.get("netLiquidityBillions"),
            "netLiquidityWeeklyDeltaBillions": liq_metrics.get("netLiquidityWeeklyDeltaBillions"),
            "netLiquidityMonthlyDeltaBillions": liq_metrics.get("netLiquidityMonthlyDeltaBillions"),
            "netLiquidityYearlyDeltaBillions": liq_metrics.get("netLiquidityYearlyDeltaBillions"),
            "policyRegime": liq_metrics.get("policyRegime"),
            "spyCorrelationR": spy_r,
            "btcCorrelationR": btc_r,
            "qqqCorrelationR": qqq_r,
            "gldCorrelationR": gld_r,
            "realGdpGrowthYoY": gdp_cpi_results.get("realGdpGrowthYoY"),
            "cpiInflationYoY": gdp_cpi_results.get("cpiInflationYoY"),
            "cpiInflationMoM": gdp_cpi_results.get("cpiInflationMoM"),
            "macroEconomicRegime": gdp_cpi_results.get("macroEconomicRegime"),
            "fedTargetReentryDate": gdp_cpi_results.get("estimated2PctTargetReentry"),
            "assetCorrelations": correlations,
            "gdpCpiAnalysis": gdp_cpi_results,
            "g20Rankings": g20_data,
            "calculatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        # Push master record to dataset
        await Actor.push_data(master_record)
        
        # Push weekly liquidity time series rows for direct chart rendering
        if include_ts:
            for _, row in df_liq_filtered.iterrows():
                await Actor.push_data({
                    "recordType": "WEEKLY_LIQUIDITY_SERIES",
                    "date": row['Date'].strftime('%Y-%m-%d'),
                    "totalAssetsBillions": round(float(row['Total_Assets']), 2),
                    "reverseRepoBillions": round(float(row['Reverse_Repo']), 2),
                    "treasuryAccountBillions": round(float(row['TGA']), 2),
                    "netLiquidityBillions": round(float(row['Net_Liquidity']), 2)
                })
                
        # Store executive summary in default Key-Value store
        summary_payload = {
            "netLiquidityOverview": liq_metrics,
            "assetCorrelations": {k: {"r": v["rCoefficient"], "relationship": v["relationship"]} for k, v in correlations.items()},
            "gdpCpiSummary": {
                "gdpGrowthYoY": gdp_cpi_results.get("realGdpGrowthYoY"),
                "cpiInflationYoY": gdp_cpi_results.get("cpiInflationYoY"),
                "macroRegime": gdp_cpi_results.get("macroEconomicRegime"),
                "target2PctReentry": gdp_cpi_results.get("estimated2PctTargetReentry")
            },
            "g20Highlights": g20_data[:5] if g20_data else []
        }
        await Actor.set_value("OUTPUT", summary_payload)
        
        Actor.log.info(f"✅ Macro Liquidity Actor completed! Master dossier and {len(df_liq_filtered) if include_ts else 0} weekly records pushed to Apify Dataset.")

if __name__ == "__main__":
    asyncio.run(main())
