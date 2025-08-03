import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime
import pytz
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# =========================
# Screener definitions
# =========================
SCREENER_CONDITIONS = {
    "episodic_pivot": {
        "name": "Episodic Pivot (4.5% GAP)",
        "condition": {
            "scan_clause": "( {cash} ( latest open > 1 day ago close * 1.05 and latest close > 20 ) )"
        }
    },
    "momentum_compression": {
        "name": "10 Year IPO Setups",
        "condition": {
            "scan_clause": "( {cash} ( ( {cash} ( latest close / 1 month ago close > 1.2 and market cap > 0 and latest max( 3 , latest high ) / latest min( 3 , latest low ) <= 1.07 and latest volume > 5000 and market cap > 100 ) ) ) )"
        }
    },
    "ipo_3_years": {
        "name": "IPO's Listed in Last 3 Years",
        "condition": {
            "scan_clause": "( {cash} ( ( {cash} ( latest volume > 10000 and market cap > 500 and( {cash} not( 800 days ago close > 0 ) ) ) ) and latest close >= 1 day ago max( 252 , latest high ) * 0.75 and latest close <= 1 day ago max( 252 , latest high ) ) )"
        }
    },
    "ipo_1_year": {
        "name": "Recent IPOs: Last 1 Year",
        "condition": {
            "scan_clause": "( {cash} ( latest volume > 10000 and market cap > 500 and( {cash} not( 250 days ago close > 0 ) ) ) )"
        }
    },
    "multi_year_breakout": {
        "name": "Multi-Year Breakout Scanner (2Y–10Y Highs)",
        "condition": {
            "scan_clause": "( {cash} ( latest high = latest max( 520 , latest high ) and latest high = latest max( 780 , latest high ) and latest high = latest max( 1040 , latest high ) and latest high = latest max( 1300 , latest high ) and latest high = latest max( 1820 , latest high ) and latest high = latest max( 1560 , latest high ) and latest high = latest max( 2080 , latest high ) and latest high = latest max( 2340 , latest high ) and latest high = latest max( 2600 , latest high ) ) )"
        }
    },
    "ten_year_range_breakout": {
        "name": "10-Year Range Multi-Year Breakout",
        "condition": {
            "scan_clause": "( {cash} ( ( {cash} ( ( {cash} ( 120 months ago high > monthly close * .9 or 119 months ago high > monthly close * .9 or 118 months ago high > monthly close * .9 or 117 months ago high > monthly close * .9 or 116 months ago high > monthly close * .9 or 115 months ago high > monthly close * .9 or 114 months ago high > monthly close * .9 or 113 months ago high > monthly close * .9 or 112 months ago high > monthly close * .9 or 111 months ago high > monthly close * .9 or 110 months ago high > monthly close * .9 or 60 months ago max( 50 , monthly high ) > monthly close * .9 ) ) and 1 month ago max( 60 , monthly high ) < monthly close ) ) ) )"
        }
    },
    "big_green_tight_consolidation": {
        "name": "Big Green Candle + 3 Tight Candles",
        "condition": {
            "scan_clause": "( {cash} ( 3 days ago \"close - 1 candle ago close / 1 candle ago close * 100\" >= 5 and latest max( 3 , latest high - latest low ) < ( 3 days ago high - 3 days ago low ) * 0.75 and ( 3 days ago high - 3 days ago low ) * 0.60 < 3 days ago close - 3 days ago open and latest close >= 52 weeks ago high * 0.75 and market cap >= 500 ) )"
        }
    },
    "multiyear_accumulation": {
        "name": "Multiyear Accumulation Dashboard",
        "condition": {
            "scan_clause": "( {cash} ( latest close > latest max( 750 , latest high ) * 0.90 and latest close < latest max( 750 , latest high ) * 1.1 and latest count( 125, 1 where latest close > 1 day ago max( 750 , latest high ) and 1 day ago close <= 2 day ago max( 750 , latest high ) ) = 0 and market cap > 200 ) )"
        }
    },
    "ipo_base_4day": {
        "name": "4 Day IPO Base (Inside Bar)",
        "condition": {
            "scan_clause": "( {cash} ( latest high < 4 days ago high and 1 day ago high < 4 days ago high and 2 days ago high < 4 days ago high and 3 days ago high < 4 days ago high and 1 day ago low > 4 days ago low and 2 days ago low > 4 days ago low and 3 days ago low > 4 days ago low and latest low > 4 days ago low and ( {cash} ( market cap > 100 and ( {cash} not( 12 months ago close > 0 ) ) and latest volume > 5000 ) ) ) )"
        }
    },
    "vcp_tightness": {
        "name": "VCP Tightness",
        "condition": {
            "scan_clause": "( {cash} ( latest ema( latest close , 10 ) <= latest ema( latest close , 50 ) * 1.03 and latest ema( close,50 ) > latest ema( close,200 ) and latest rsi( 14 ) >= 45 and market cap >= 500 and latest ema( close,200 ) > 1 month ago ema( close,200 ) and latest high <= 1 day ago high and latest low >= 1 day ago low ) )"
        }
    },
    "ipo_base": {
        "name": "IPO Base Scan",
        "condition": {
            "scan_clause": "( {cash} ( market cap > 100 and( {cash} not( 12 months ago close > 0 ) ) and latest volume > 5000 ) )"
        }
    },
    "all_tradable_stocks": {
        "name": "All Tradable Stocks",
        "condition": {
            "scan_clause": "( {cash} ( latest close > 25 and latest close <= 10000 and market cap >= 300 and latest {custom_indicator_176230_start}\"(  sma(  close , 50 ) *  sma(  volume , 50 ) ) / 10000000\"{custom_indicator_176230_end} >= 5 ) )"
        }
    },
    "smc_tradable_universe_near_ath": {
        "name": "SMC Tradable Universe: 25% Near ATH Stocks",
        "condition": {
            "scan_clause": "( {cash} ( latest close >= 10 years ago high * 0.75 and market cap >= 500 and latest close > 20 and latest volume > 5000 and latest close > latest \"wma( ( ( 2 * wma( (latest close), 100) ) - wma((latest close), 200) ), 14)\" and latest close > latest \"wma( ( ( 2 * wma( (latest close), 25) ) - wma((latest close), 50) ), 7)\" ) )"
        }
    },
    "minervini_stage_2": {
        "name": "Minervini Stage 2 Stocks",
        "condition": {
            "scan_clause": "( {cash} ( ( {cash} ( latest close > latest ema( close,50 ) and latest ema( close,50 ) > latest ema( close,150 ) and latest ema( close,150 ) > latest ema( close,200 ) and latest close >= 1.33 * weekly min( 52 , weekly low ) and latest close * 1.43 >= weekly max( 52 , weekly high ) and latest ema( close,200 ) > 1 month ago ema( close,200 ) and latest close >= 25 and latest volume > 1000 and latest close > 1 day ago min( 504 , latest low ) * 1.5 ) ) ) )"
        }
    },
    "epo_intraday": {
        "name": "EPo (Intraday Opportunities)",
        "condition": {
            "scan_clause": "( {cash} ( ( {cash} ( latest close > 1 day ago close * 1.06 and latest volume > latest sma( latest volume , 20 ) * 4 and latest close > 1 day ago max( 20 , latest close ) and ( latest close - latest low ) / ( latest high - latest low ) > 0.7 and latest close * latest volume > 500000 ) ) ) )"
        }
    },
    "hve_highest_volume_ever": {
        "name": "Highest Volume – EVER (HVE)",
        "condition": {
            "scan_clause": "( {cash} ( ( {cash} ( latest volume >= 1 day ago max( 600 , latest volume ) and latest \"close - 1 candle ago close / 1 candle ago close * 100\" >= 0 and market cap > 500 ) ) ) )"
        }
    },
    "hvy_highest_volume_yearly": {
        "name": "Highest Volume – YEARLY (HVY)",
        "condition": {
            "scan_clause": "( {cash} ( ( {cash} ( ( {cash} ( latest volume = ( latest max( 252 , latest volume ) ) or latest close >= 20 or market cap >= 100 or weekly sma( weekly volume , 10 ) > 100000 or latest sma( latest volume , 50 ) * latest close > 500000 or latest close >= 1 day ago close ) ) ) ) ) )"
        }
    },
    "hve_hvy_hvq": {
        "name": "HVE / HVY / HVQ (Highest Volume Combined)",
        "condition": {
            "scan_clause": """( {cash} ( 
                ( {cash} ( 
                    ( {cash} ( 
                        latest volume = ( latest max( 2000 , latest volume ) ) 
                        or latest volume = ( latest max( 252 , latest volume ) ) 
                        or latest volume = ( latest max( 63 , latest volume ) ) 
                    ) ) 
                    and ( {cash} ( 
                        latest close >= 20 
                        and market cap >= 100 
                        and weekly sma( weekly volume , 10 ) > 100000 
                        and latest sma( latest volume , 50 ) * latest close > 5000000 
                    ) ) 
                    and latest close >= 1 day ago close 
                ) ) 
            ) )"""
        }
    },
    "volume_buzz": {
        "name": "Volume Buzz",
        "condition": {
            "scan_clause": """( {cash} (
                ( {cash} (
                    ( {cash} (
                        latest volume > latest max( 10 , latest volume * latest count( 1 , 1 where latest close < latest open ) )
                        or ( {cash} (
                            ( {cash} ( 1 day ago close > 2 days ago close )
                                or ( {cash} ( 1 day ago close < 2 days ago close and 1 day ago volume < latest volume ) )
                            )
                            and ( {cash} ( 2 days ago close > 3 days ago close
                                or ( {cash} ( 2 days ago close < 3 days ago close and 2 days ago volume < latest volume ) )
                            ) )
                            and ( {cash} ( 3 days ago close > 4 days ago close
                                or ( {cash} ( 3 days ago close < 4 days ago close and 3 days ago volume < latest volume ) )
                            ) )
                            and ( {cash} ( 4 days ago close > 5 days ago close
                                or ( {cash} ( 4 days ago close < 5 days ago close and 4 days ago volume < latest volume ) )
                            ) )
                            and ( {cash} ( 5 days ago close > 6 days ago close
                                or ( {cash} ( 5 days ago close < 6 days ago close and 5 days ago volume < latest volume ) )
                            ) )
                            and ( {cash} ( 6 days ago close > 7 days ago close
                                or ( {cash} ( 6 days ago close < 7 days ago close and 6 days ago volume < latest volume ) )
                            ) )
                            and ( {cash} ( 7 days ago close > 8 days ago close
                                or ( {cash} ( 7 days ago close < 8 days ago close and 7 days ago volume < latest volume ) )
                            ) )
                            and ( {cash} ( 8 days ago close > 9 days ago close
                                or ( {cash} ( 8 days ago close < 9 days ago close and 8 days ago volume < latest volume ) )
                            ) )
                            and ( {cash} ( 9 days ago close > 10 days ago close
                                or ( {cash} ( 9 days ago close < 10 days ago close and 9 days ago volume < latest volume ) )
                            ) )
                        and ( {cash} ( 10 days ago close > 11 days ago close
                          or ( {cash} ( 10 days ago close < 11 days ago close and 10 days ago volume < latest volume ) )
                        ) )
                    ) )
                ) )
            ) )
            and latest close >= 1 day ago close
            and ( {cash} (
                latest close >= 20
                and market cap >= 100
                and weekly sma( weekly volume , 10 ) > 100000
                and latest sma( latest volume , 50 ) * latest close > 5000000
            ) )
            and ( {cash} (
                latest close > latest sma( latest close , 50 )
                and latest close > latest sma( latest close , 200 )
                and latest close > 1.3 * weekly min( 52 , weekly low )
                and latest close > 0.75 * weekly max( 52 , weekly high )
                and latest low <= latest wma( latest close , 10 )
            ) )
            ) )"""
        }
    },
    "flags_formation": {
        "name": "Flags Formation",
        "condition": {
        "scan_clause": """( {cash} (
            ( {cash} (
                    latest close > 25
                    and latest close <= 10000
                    and market cap >= 300
                    and weekly "close - 1 candle ago close / 1 candle ago close * 100" > 19
                    and latest {custom_indicator_176230_start}"( sma( close , 50 ) * sma( volume , 50 ) ) / 10000000"{custom_indicator_176230_end} > 5
                ) )
            ) )"""
        }
    },
    "tight_flag": {
        "name": "Tight Flag",
        "condition": {
            "scan_clause": """( {cash} (
                ( {cash} (
                    latest close / 1 month ago close > 1.2
                    and market cap > 0
                    and latest max( 3 , latest high ) / latest min( 3 , latest low ) <= 1.07
                    and latest volume > 5000
                    and latest close > 20
                ) )
            ) )"""
        }
    },
    "tight_weekly_base": {
        "name": "Tight Weekly Base",
        "condition": {
            "scan_clause": """( {cash} ( ( {cash} ( ( {cash} ( ( {cash} ( 
                latest high > 50 
                and latest close > latest sma( latest close , 20 ) 
                and latest sma( latest volume , 50 ) >= 5000 
                and latest close > latest ema( latest close , 50 ) 
                and abs( ( weekly max( 3 , weekly close ) / weekly min( 3 , weekly close ) - 1 ) * 100 ) <= 2 
                and ( ( 3 weeks ago max( 12 , weekly close ) / 3 weeks ago min( 12 , weekly close ) - 1 ) * 100 ) >= 30 
                and latest {custom_indicator_176230_start}"( sma( close , 50 ) * sma( volume , 50 ) ) / 10000000"{custom_indicator_176230_end} > 5 
            ) ) ) ) ) ) ) )"""
        }
    },
    "power_trend_squeeze": {
        "name": "Power Trend Squeeze",
        "condition": {
            "scan_clause": """( {cash} ( ( {cash} ( ( {cash} ( 
                latest close > latest sma( close,200 ) 
                and latest close > latest sma( close,150 ) 
                and latest sma( close,150 ) > latest sma( close,200 ) 
                and latest sma( close,200 ) > 25 days ago sma( close,200 ) 
                and latest sma( close,50 ) > latest sma( close,150 ) 
                and latest close > latest sma( close,50 ) 
                and latest close > 30 
                and 1 day ago close * 0.02 >= ( 1 day ago high - 1 day ago low ) 
            ) ) ) ) ) )"""
        }
    },
    "darvas_box": {
        "name": "Darvas Box",
        "condition": {
            "scan_clause": """( {cash} ( ( {cash} (
                latest close >= 20
                and market cap >= 500
                and ( {cash} (
                    3 days ago high > 2 days ago high
                    and 3 days ago high > 1 day ago high
                    and 3 days ago high > latest high
                    and 3 days ago low < 2 days ago low
                    and 3 days ago low < 1 day ago low
                    and 3 days ago low < latest low
                ) )
            ) ) ) )"""
        }
    },
    "golden_crossover": {
        "name": "Golden Crossover (50EMA > 200EMA)",
        "condition": {
            "scan_clause": """( {cash} ( ( {cash} (
                latest ema( latest close , 50 ) > latest ema( latest close , 200 )
                and 1 day ago ema( latest close , 50 ) <= 1 day ago ema( latest close , 200 )
                and latest {custom_indicator_176230_start}"(
                    sma( close , 50 ) * sma( volume , 50 )
                ) / 10000000"{custom_indicator_176230_end} > 5
            ) ) ) )"""
        }
    },
    "liquid_ipos_2y": {
        "name": "Liquid IPOs (2Y)",
        "condition": {
            "scan_clause": """( {cash} ( ( {cash} ( ( {cash} (
                latest close > 20
                and latest ema( latest volume , 20 ) > 50000
                and ( {cash} not( 2 years ago close > 0 ) )
                and weekly high < 1 week ago high * 1.01
                and weekly low > 1 week ago low * 0.99
                and market cap > 100
            ) ) ) ) ) )"""
        }
    },
    "stocks_near_highs": {
        "name": "Stocks Near Highs",
        "condition": {
            "scan_clause": """( {cash} ( ( {cash} (
                latest close >= weekly max( 52 , weekly high ) * 0.75
                and latest close >= weekly max( 52 , weekly low ) * 1
                and latest close >= 30
                and market cap <= 30000
                and latest close > latest sma( close,200 )
                and latest close > latest sma( close,50 )
                and latest sma( close,50 ) > latest sma( close,200 )
                and latest close <= 3000
                and latest sma( close,200 ) > 1 month ago sma( close,200 )
                and 1 month ago sma( close,200 ) > 2 months ago sma( close,200 )
                and 2 months ago sma( close,200 ) > 3 months ago sma( close,200 )
            ) ) ) )"""
        }
    },
    "vcp_minervini": {
        "name": "Volatility Contraction Pattern (VCP) - Mark Minervini",
        "condition": {
            "scan_clause": """( {cash} (
                weekly ema( close,13 ) > weekly ema( close,26 )
                and weekly ema( close,26 ) > weekly sma( close,50 )
                and weekly sma( close,40 ) > 5 weeks ago sma( close,40 )
                and latest close >= weekly min( 50 , weekly low * 1.3 )
                and latest close >= weekly max( 50 , weekly high * 0.75 )
                and 20 days ago ema( close,13 ) > 20 weeks ago ema( close,26 )
                and 5 weeks ago sma( close,40 ) > 10 weeks ago sma( close,40 )
                and latest close > latest sma( close,50 )
                and ( weekly wma( close,8 ) - weekly sma( close,8 ) ) * 6 / 29 < 0.5
                and latest close > 10
            ) )"""
        }
    },
    "perfectly_stacked_ma": {
        "name": "Perfectly Stacked Moving Average",
        "condition": {
            "scan_clause": """( {cash} ( 
                ( {cash} (
                    weekly ema( weekly close , 13 ) > weekly ema( weekly close , 26 )
                    and weekly ema( weekly close , 26 ) > weekly sma( weekly close , 50 )
                    and weekly sma( weekly close , 40 ) > 5 weeks ago sma( 5 weeks ago close , 40 )
                    and latest close >= weekly min( 50 , weekly low * 1.3 )
                    and latest close >= weekly max( 50 , weekly high * 0.75 )
                    and 20 days ago ema( 20 days ago close , 13 ) > 20 weeks ago ema( 20 weeks ago close , 26 )
                    and 5 weeks ago sma( weekly close , 40 ) > 10 weeks ago sma( 5 weeks ago close , 40 )
                    and latest close > latest sma( latest close , 50 )
                    and ( weekly wma( weekly close , 8 ) - weekly sma( weekly close , 8 ) ) * 6 / 29 < 0.5
                    and latest close > 100
                    and latest close > latest open
                    and latest close > weekly open
                    and latest close > monthly open
                    and latest low > 1 day ago close - abs( 1 day ago close / 222 )
                    and latest volume * latest close >= 10000000
                ) )
            ) )"""
        }
    },
    "high_flags": {
        "name": "High Flags",
        "condition": {
            "scan_clause": """( {cash} ( 
                ( {cash} (
                    ( latest max( 60 , latest high - 60 days ago close ) ) / 60 days ago close > 0.70
                    and latest max( 20 , latest high ) < latest max( 60 , latest high )
                    and latest min( 20 , latest close ) > 1 day ago max( 250 , latest high ) * 0.80
                ) )
            ) )"""
        }
    },
    "promoter_stake_increase": {
        "name": "Promoter Stake Increase (>1%)",
        "condition": {
            "scan_clause": """( {cash} (
                ( {cash} (
                    quarterly indian promoter and group shareholders > 1 quarter ago indian promoter and group shareholders * 1.01
                    and quarterly insurance companies percentage > 2
                ) )
            ) )"""
        }
    },
    "retail_stake_increase": {
        "name": "Retail Stake Increase (>3%)",
        "condition": {
            "scan_clause": """( {cash} (
                ( {cash} (
                    ( quarterly individuals share capital up to rs 1 lakh percentage +
                    quarterly individuals share capital in excess of rs 1 lakh percentage )
                    > ( 1 quarter ago individuals share capital up to rs 1 lakh percentage +
                        1 quarter ago individuals share capital in excess of rs 1 lakh percentage ) * 1.03
                    and
                    ( quarterly individuals share capital up to rs 1 lakh percentage +
                    quarterly individuals share capital in excess of rs 1 lakh percentage )
                    > ( 4 quarters ago individuals share capital up to rs 1 lakh percentage +
                        4 quarters ago individuals share capital in excess of rs 1 lakh percentage ) * 1.03
                ) )
            ) )"""
        }
    },
    "fii_dii_stake_increase": {
        "name": "FII + DII Stake Increase (1Q)",
        "condition": {
            "scan_clause": """( {cash} (
                ( {cash} (
                    quarterly foreign institutional investors percentage >
                    1 quarter ago foreign institutional investors percentage
                    and
                    quarterly mutual funds or uti percentage >
                    1 quarter ago mutual funds or uti percentage
                ) )
            ) )"""
        }
    },
    "consistent_mf_fii_accumulation": {
        "name": "Consistent MF & FII Accumulation (4Q)",
        "condition": {
            "scan_clause": """( {cash} (
                ( {cash} (
                    ( {cash} (
                        quarterly mutual funds or uti percentage >
                        1 quarter ago mutual funds or uti percentage
                        and
                        1 quarter ago mutual funds or uti percentage >
                        2 quarter ago mutual funds or uti percentage
                        and
                        2 quarter ago mutual funds or uti percentage >
                        3 quarter ago mutual funds or uti percentage
                        and
                        quarterly foreign institutional investors percentage >
                        1 quarter ago foreign institutional investors percentage
                        and
                        1 quarter ago foreign institutional investors percentage >
                        2 quarter ago foreign institutional investors percentage
                        and
                        2 quarter ago foreign institutional investors percentage >
                        3 quarter ago foreign institutional investors percentage
                    ) )
                ) )
            ) )"""
        }
    },
}

# =========================
# Category mapping
# =========================
SCREENER_CATEGORIES = {
    "All Screeners":[
        "minervini_stage_2",
        "smc_tradable_universe_near_ath",
        "all_tradable_stocks",
        "ipo_1_year",
        "ipo_3_years",
        "momentum_compression",
        "multi_year_breakout",
        "ten_year_range_breakout",
        "episodic_pivot", #4.5%  
        "epo_intraday",
        "hve_highest_volume_ever",
        "hvy_highest_volume_yearly",
        "hve_hvy_hvq",
        "volume_buzz",
        "flags_formation",
        "tight_flag",
        "tight_weekly_base",
        "power_trend_squeeze",
        "darvas_box",
        "golden_crossover",
        "liquid_ipos_2y",
        "stocks_near_highs",
        "vcp_minervini",
        "high_flags",
        "perfectly_stacked_ma",
        "promoter_stake_increase",
        "retail_stake_increase",
        "consistent_mf_fii_accumulation",
        "fii_dii_stake_increase"
    ],
    "Tradable Universe": [
        "minervini_stage_2",
        "smc_tradable_universe_near_ath",
        "all_tradable_stocks"
    ],
    "IPO Base": [
        "ipo_1_year",
        "ipo_3_years",
        "momentum_compression"
    ],
    "Multi-Year High Breakout": [
        "multi_year_breakout",
        "ten_year_range_breakout",
    ],
    "Episodic Pivot":[
      "episodic_pivot", #4.5%  
      "epo_intraday"
    ],
    "Volume":[
        "hve_highest_volume_ever",
        "hvy_highest_volume_yearly",
        "hve_hvy_hvq",
        "volume_buzz"
    ],
    "Flags":[
        "flags_formation",
        "tight_flag",
        "tight_weekly_base"
    ],
    "Special category":[
        "power_trend_squeeze",
        "darvas_box",
        "golden_crossover",
        "liquid_ipos_2y",
        "stocks_near_highs",
        "vcp_minervini",
        "high_flags",
        "perfectly_stacked_ma"
    ],
    "Fundamental Screeners":[
        "promoter_stake_increase",
        "retail_stake_increase",
        "consistent_mf_fii_accumulation",
        "fii_dii_stake_increase"
    ]
}

# =========================
# Main index view
# =========================
@login_required(login_url='/login/')
def index(request):
    stock_list = None
    last_updated = None
    selected_screener = request.POST.get("screener_name")
    selected_screener_name = ""
    selected_category = request.GET.get("category")

    # Show screeners by category
    if selected_category and selected_category in SCREENER_CATEGORIES:
        filtered_screeners = {
            key: SCREENER_CONDITIONS[key]
            for key in SCREENER_CATEGORIES[selected_category]
            if key in SCREENER_CONDITIONS
        }
    else:
        # Default: show all
        filtered_screeners = SCREENER_CONDITIONS

    # Run scan if user selects screener
    if request.method == "POST" and selected_screener:
        screener = SCREENER_CONDITIONS.get(selected_screener)
        selected_screener_name = screener["name"] if screener else ""
        condition = screener["condition"] if screener else {}

        url = "https://chartink.com/screener/process"
        try:
            with requests.session() as s:
                r_data = s.get(url)
                soup = bs(r_data.content, "lxml")
                meta = soup.find("meta", {"name": "csrf-token"})
                header = {"x-csrf-token": meta["content"]} if meta else {}

                response = s.post(url, headers=header, data=condition)
                data = response.json()
                raw_data = data["data"]

                filtered_data = [
                    row for row in raw_data
                    if all(k in row for k in ["nsecode", "per_chg", "close", "volume", "sr"])
                ]

                stock_list = pd.DataFrame(filtered_data).rename(columns={
                    "nsecode": "stock_name",
                    "per_chg": "percent_change",
                    "close": "current_price",
                    "volume": "trade_volume",
                    "sr": "rank"
                }).to_dict(orient="records")

                last_updated = datetime.now(pytz.timezone('Asia/Kolkata'))

        except Exception as e:
            print(f"Error: {e}")
            stock_list = []

    return render(request, 'stock_app/index.html', {
        'stock_list': stock_list,
        'last_updated': last_updated,
        'screeners': filtered_screeners,
        'selected_screener': selected_screener,
        'selected_screener_name': selected_screener_name,
        'categories': SCREENER_CATEGORIES.keys(),
        'selected_category': selected_category
    })

# =========================
# CSV download view
# =========================
def download_csv(request):
    selected_screener = request.GET.get("screener_name", "episodic_pivot")
    screener = SCREENER_CONDITIONS.get(selected_screener)
    condition = screener["condition"] if screener else {}

    url = "https://chartink.com/screener/process"
    try:
        with requests.session() as s:
            r_data = s.get(url)
            soup = bs(r_data.content, "lxml")
            meta = soup.find("meta", {"name": "csrf-token"})
            header = {"x-csrf-token": meta["content"]} if meta else {}

            response = s.post(url, headers=header, data=condition)
            data = response.json()
            raw_data = data["data"]

            filtered_data = [
                row for row in raw_data
                if all(k in row for k in ["nsecode", "per_chg", "close", "volume", "sr"])
            ]

            df = pd.DataFrame(filtered_data).rename(columns={
                "sr": "Rank",
                "nsecode": "Stock Symbol",
                "per_chg": "Percent Change",
                "close": "Current Price",
                "volume": "Trade Volume"
            })

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{selected_screener}_stocks.csv"'
            df.to_csv(path_or_buf=response, index=False)
            return response

    except Exception as e:
        print("CSV download error:", e)
        return HttpResponse("Error downloading CSV")
    
