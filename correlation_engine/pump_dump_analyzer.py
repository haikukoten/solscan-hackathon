"""Analyzes token transactions for pump and dump patterns."""

import logging
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import openai

from config import settings

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

def analyze_token_transactions(token_data: Dict[str, Any], extracted_tweets: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyzes token transaction data for pump and dump patterns.
    
    Args:
        token_data: Dictionary containing token transaction data
        extracted_tweets: Optional list of tweets mentioning this token
        
    Returns:
        Dictionary with analysis results
    """
    if not token_data:
        logger.warning("No token data provided for analysis")
        return {"is_pump_dump": False, "confidence": 0, "reason": "No transaction data provided"}
    
    # Extract key metrics
    token_address = token_data.get("token_address", "Unknown")
    total_txns = token_data.get("total_transactions", 0)
    buy_txns = token_data.get("buy_transactions", 0)
    sell_txns = token_data.get("sell_transactions", 0)
    unique_wallets = token_data.get("unique_wallets", 0)
    
    # Basic heuristic analysis
    if total_txns < 10:
        logger.info(f"Insufficient transactions ({total_txns}) for token {token_address}")
        return {
            "is_pump_dump": False, 
            "confidence": 0.1, 
            "reason": f"Insufficient data: only {total_txns} transactions found"
        }
    
    # Convert hourly volumes to a time series for analysis
    hourly_volumes = token_data.get("hourly_volumes", {})
    volume_data = []
    for hour_ts, volume in sorted(hourly_volumes.items()):
        hour_dt = datetime.fromtimestamp(float(hour_ts))
        volume_data.append({"timestamp": hour_dt.isoformat(), "volume": volume})
    
    # Check for volume spikes (simple heuristic)
    has_volume_spike = False
    volume_spike_factor = 0
    previous_volumes = []
    
    if len(volume_data) >= 3:
        for i in range(2, len(volume_data)):
            current_vol = volume_data[i]["volume"]
            avg_prev_vol = sum(v["volume"] for v in volume_data[i-2:i]) / 2
            
            if avg_prev_vol > 0 and current_vol > avg_prev_vol * 3:  # 3x spike
                has_volume_spike = True
                volume_spike_factor = current_vol / avg_prev_vol
                logger.info(f"Volume spike detected: {volume_spike_factor:.2f}x increase")
                break
    
    # Analyze wallet patterns
    wallets = token_data.get("wallets", {})
    
    # Find wallets with high net outflow (potential dumpers)
    potential_dumpers = []
    for wallet_addr, stats in wallets.items():
        # If wallet has received tokens and then sent out significantly more
        if stats["received"] > 0 and stats["sent"] > stats["received"] * 1.5:
            potential_dumpers.append({
                "address": wallet_addr,
                "received": stats["received"],
                "sent": stats["sent"],
                "net": stats["net"],
                "dump_ratio": stats["sent"] / stats["received"] if stats["received"] > 0 else 0
            })
    
    # Sort dumpers by dump ratio (highest first)
    potential_dumpers.sort(key=lambda x: x["dump_ratio"], reverse=True)
    
    # Find wallets with high concentration (potential whales/insiders)
    total_supply = sum(w["received"] for w in wallets.values())
    whale_threshold = total_supply * 0.1  # 10% of total supply
    
    potential_whales = []
    for wallet_addr, stats in wallets.items():
        if stats["received"] > whale_threshold:
            potential_whales.append({
                "address": wallet_addr,
                "received": stats["received"],
                "percent_of_supply": (stats["received"] / total_supply) * 100 if total_supply > 0 else 0
            })
    
    # Sort whales by holdings (highest first)
    potential_whales.sort(key=lambda x: x["received"], reverse=True)
    
    # Calculate preliminary confidence based on heuristics
    pump_dump_confidence = 0.0
    
    # Factor 1: Buy/sell ratio - higher sell ratio is suspicious
    if buy_txns + sell_txns > 0:
        sell_ratio = sell_txns / (buy_txns + sell_txns)
        if sell_ratio > 0.7:  # More than 70% are sells
            pump_dump_confidence += 0.2
    
    # Factor 2: Volume spikes
    if has_volume_spike:
        if volume_spike_factor > 10:
            pump_dump_confidence += 0.3
        elif volume_spike_factor > 5:
            pump_dump_confidence += 0.2
        else:
            pump_dump_confidence += 0.1
    
    # Factor 3: Dumpers presence
    if len(potential_dumpers) > 0:
        if len(potential_dumpers) > 5:
            pump_dump_confidence += 0.2
        else:
            pump_dump_confidence += 0.1
    
    # Factor 4: Wallet concentration
    top_5_percent = sum(1 for w in potential_whales if w["percent_of_supply"] > 5)
    if top_5_percent >= 3:  # 3+ wallets with 5%+ supply
        pump_dump_confidence += 0.2
    
    # Determine if this looks like a pump and dump
    is_pump_dump = pump_dump_confidence > 0.5
    reasons = []
    
    if sell_ratio > 0.7:
        reasons.append(f"High sell ratio ({sell_ratio:.2f})")
    if has_volume_spike:
        reasons.append(f"Volume spike ({volume_spike_factor:.2f}x)")
    if len(potential_dumpers) > 0:
        reasons.append(f"Found {len(potential_dumpers)} potential dumpers")
    if top_5_percent >= 3:
        reasons.append(f"High concentration: {top_5_percent} wallets hold 5%+ of supply")
    
    # Use AI for deeper analysis if we have the API key
    ai_analysis = {}
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "YOUR_OPENAI_API_KEY":
        try:
            ai_analysis = analyze_with_ai(token_data, extracted_tweets)
            
            # If AI analysis is confident, it overrides our heuristic
            if ai_analysis.get("confidence", 0) > pump_dump_confidence:
                is_pump_dump = ai_analysis.get("is_pump_dump", is_pump_dump)
                pump_dump_confidence = ai_analysis.get("confidence", pump_dump_confidence)
                
                # Add AI reasons
                ai_reasons = ai_analysis.get("reasons", [])
                if ai_reasons:
                    reasons.extend(ai_reasons)
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
    
    # Prepare the result
    result = {
        "token_address": token_address,
        "is_pump_dump": is_pump_dump,
        "confidence": pump_dump_confidence,
        "reasons": reasons,
        "potential_dumpers": potential_dumpers[:5],  # Top 5 dumpers
        "top_holders": potential_whales[:5],  # Top 5 whales
        "volume_analysis": {
            "has_spike": has_volume_spike,
            "spike_factor": volume_spike_factor,
            "hourly_data": volume_data
        },
        "transaction_summary": {
            "total": total_txns,
            "buys": buy_txns,
            "sells": sell_txns,
            "unique_wallets": unique_wallets
        }
    }
    
    if ai_analysis:
        result["ai_analysis"] = {
            "confidence": ai_analysis.get("confidence", 0),
            "summary": ai_analysis.get("summary", ""),
            "detailed_report": ai_analysis.get("detailed_report", "")
        }
    
    # Save the analysis to a file
    try:
        clean_address = token_address.replace("/", "_").replace(":", "_")
        os.makedirs("./data/analysis", exist_ok=True)
        
        with open(f"./data/analysis/token_{clean_address}_analysis.json", 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Saved token analysis for {token_address}")
    except Exception as e:
        logger.error(f"Error saving analysis: {e}")
    
    return result

def analyze_with_ai(token_data: Dict[str, Any], extracted_tweets: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Uses AI to analyze detailed token data and social signals for pump and dump patterns.
    
    Args:
        token_data: Dictionary containing detailed token data (transfers, meta, holders, defi)
        extracted_tweets: Optional list of tweets mentioning this token
        
    Returns:
        Dictionary with AI analysis results, including detailed narrative.
    """
    
    logger.info("Performing AI analysis on enriched token data...")
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # --- Prepare context for the AI ---
    token_address = token_data.get('token_address', 'Unknown')
    wallets = token_data.get('wallets', {})
    hourly_volumes = token_data.get('hourly_volumes', {})
    raw_transactions = token_data.get('raw_transactions', [])
    metadata = token_data.get('metadata', {})
    holders_page_1 = token_data.get('holders_page_1', [])
    defi_activities_page_1 = token_data.get('defi_activities_page_1', [])
    
    # --- Create Summaries for Prompt --- 
    
    # Basic Stats Summary
    basic_stats_summary = (
        f"- Token Address: {token_address}\n"
        f"- Total Transactions Analyzed: {token_data.get('total_transactions', 0)}\n"
        f"- Unique Wallets Involved: {len(wallets)}"
    )
    
    # Metadata Summary
    meta_summary = "Token metadata not available."
    if metadata:
        meta_summary = (
            f"- Name: {metadata.get('name', 'N/A')}\n"
            f"- Symbol: {metadata.get('symbol', 'N/A')}\n"
            f"- Decimals: {metadata.get('decimals', 'N/A')}\n"
            f"- Total Supply: {metadata.get('supply', 'N/A')}\n"
            f"- Holders (from meta): {metadata.get('holder', 'N/A')}"
        )

    # Top Holders Summary (from explicit /holders call)
    top_holders_summary = "Holder data not available or empty."
    if holders_page_1:
        top_holders_summary = f"Top {len(holders_page_1)} holders (Page 1):\n"
        for i, holder in enumerate(holders_page_1[:5]): # Show top 5 from page 1
             owner = holder.get('owner', 'N/A')
             amount = holder.get('amount', 0)
             # Calculate percentage if supply and decimals are known
             supply_str = metadata.get('supply', '0')
             decimals_raw = metadata.get('decimals') # Get raw value without default
             percentage = "N/A" # Default to N/A
             formatted_amount_str = str(amount) # Default to raw amount string

             # Check if decimals is a valid number (int or float)
             decimals_valid = False
             if decimals_raw is not None:
                 try:
                     decimals = int(decimals_raw) # Try converting to int
                     decimals_valid = True
                 except (ValueError, TypeError):
                     # ... (rest of decimal validation logic remains the same) ...
                     pass # Keep decimals_valid as False for now

             # Format amount string if decimals are valid
             if decimals_valid:
                 try:
                     amount_int = int(amount)
                     formatted_amount = amount_int / (10**decimals)
                     # Format with reasonable precision, adjust as needed
                     formatted_amount_str = f"{formatted_amount:,.4f}" 
                 except (ValueError, TypeError):
                     formatted_amount_str = f"{amount} (Raw)" # Indicate raw if conversion fails

             # Proceed only if we have valid numbers for percentage
             if supply_str.isdigit() and decimals_valid:
                 try: 
                     supply = int(supply_str)
                     amount_int = int(amount)
                     percentage = f"{(amount_int / supply) * 100:.4f}%"
                 except (ValueError, TypeError) as calc_err:
                     logger.error(f"Error calculating percentage for holder {owner}: {calc_err}")
                     percentage = "N/A"
                         
             # Use the formatted amount string in the report line
             top_holders_summary += f"  - Holder #{i+1}: {owner[:6]}... (Amount: {formatted_amount_str}, Approx: {percentage})\n"
        
    # Top Net Sellers Summary (Calculated from transfers)
    net_sellers = []
    for addr, data in wallets.items():
        net_change = data['received'] - data['sent']
        if net_change < 0: net_sellers.append({"address": addr, "net_sold": -net_change})
    sorted_net_sellers = sorted(net_sellers, key=lambda item: item['net_sold'], reverse=True)
    top_sellers_summary = "No significant net sellers found."
    if sorted_net_sellers:
        top_sellers_summary = "Top 5 Net Sellers (Calculated):\n"
        for i, seller_data in enumerate(sorted_net_sellers[:5]):
             top_sellers_summary += f"  - Seller #{i+1}: {seller_data['address'][:6]}... (Net Sold: {seller_data['net_sold']:.2f})\n"
        
    # Raw Transaction Sample Summary
    raw_tx_sample_summary = "No raw transaction sample available."
    if raw_transactions:
        raw_tx_sample_summary = f"Sample of first {min(len(raw_transactions), 25)} raw transactions:\n"
        for i, tx in enumerate(raw_transactions[:25]): 
            ts = datetime.fromtimestamp(tx.get('blockTime', 0)).strftime('%Y-%m-%d %H:%M:%S')
            src = tx.get('from_address', tx.get('src', 'N/A'))
            dst = tx.get('to_address', tx.get('dst', 'N/A'))
            amt = tx.get('amount', 0)
            is_dex_like = "exchange" in dst.lower() or "swap" in dst.lower() or "pool" in dst.lower()
            raw_tx_sample_summary += f"- {ts}: {src[:6]}.. -> {dst[:6]}.. ({amt}) {'[DEX?]' if is_dex_like else ''}\n"

    # DeFi Activity Sample Summary
    defi_activity_summary = "No recent DeFi activity data available."
    if defi_activities_page_1:
        defi_activity_summary = f"Sample of recent {len(defi_activities_page_1)} DeFi activities (Page 1):\n"
        for i, activity in enumerate(defi_activities_page_1[:5]): # Show top 5 from page 1
            ts = datetime.fromtimestamp(activity.get('block_time', 0)).strftime('%Y-%m-%d %H:%M:%S')
            act_type = activity.get('activity_type', 'Unknown')
            platform = activity.get('platform', ['Unknown'])[0][:10] # First platform, truncated
            value = activity.get('value', 'N/A')
            defi_activity_summary += f"  - {ts}: {act_type} on {platform} (Value: ${value:.2f})\n"

    # Tweet Summary
    tweet_summary = "No specific tweets provided for this token."
    if extracted_tweets:
        tweet_summary = f"Analysis should consider {len(extracted_tweets)} related tweets. Examples:\n"
        for i, tweet in enumerate(extracted_tweets[:3]):
            text = tweet.get('text', '')[:100]
            author = tweet.get('author', {}).get('userName', 'Unknown')
            tweet_summary += f"- @{author}: \"{text}...\"\n"
            
    # --- AI Prompt --- 
    prompt = f"""
    Analyze the following detailed Solana token data ({token_address}) and social context for pump and dump characteristics. Provide a detailed narrative.

    **Token Metadata:**
    {meta_summary}

    **Holder Information:**
    {top_holders_summary}

    **Transaction Overview:**
    {basic_stats_summary}
    {top_sellers_summary}

    **Recent DeFi Activity Sample:**
    {defi_activity_summary}

    **Raw Transaction Sample (Timestamp: From -> To (Amount) [DEX?]):**
    {raw_tx_sample_summary}

    **Social Context:**
    {tweet_summary}

    **Analysis Request:**
    1.  Based on ALL provided data (metadata, holders, transfers, defi activity, social), determine if this token is likely a pump and dump scheme (True/False).
    2.  Provide a confidence score (0.0 to 1.0).
    3.  Write a detailed narrative explaining **how**, **why**, and **when** this appears to be a pump and dump. Reference specific patterns from **all data sources**: token creation/supply details, holder distribution, raw transaction flow (buys/sells, DEX interactions), DeFi activity (swaps, liquidity), volume changes, timing relative to social promotions, and social signals (hype language).
    4.  Identify specific potential dumper wallet addresses based on **all available evidence** (e.g., early holders selling, large net sellers, wallets interacting with DEXs after hype). List these addresses clearly.
    5.  Provide a concise summary conclusion.

    **Output Format (JSON):**
    {{
      "is_pump_dump": boolean,
      "confidence": float,
      "summary": "Concise summary conclusion.",
      "detailed_narrative": "Detailed explanation covering how, why, when, analysis of all data sources (meta, holders, transfers, defi, social), and potential dumpers.",
      "potential_dumpers": ["wallet_address_1", "wallet_address_2", ...]
    }}
    """
    
    # --- Log the prompt ---
    logger.debug(f"Sending the following prompt to AI for token {token_address}:\n{prompt}")
    
    # --- API Call --- 
    try:
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert crypto analyst specializing in detecting pump and dump schemes on Solana. Analyze the provided comprehensive data (metadata, holders, transfers, defi activity, social context), paying close attention to wallet activity and transaction flow, and return your findings in the specified JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        ai_result_str = response.choices[0].message.content
        ai_result = json.loads(ai_result_str)
        logger.info(f"AI analysis complete: is_pump_dump={ai_result.get('is_pump_dump')}, confidence={ai_result.get('confidence')}")
        # --- Log the raw response ---
        logger.debug(f"Received raw AI response for token {token_address}:\n{ai_result_str}")
        return ai_result
        
    except Exception as e:
        logger.error(f"Error during AI analysis: {e}")
        return {
            "is_pump_dump": False,
            "confidence": 0.0,
            "summary": "AI analysis failed.",
            "detailed_narrative": f"Error during analysis: {e}",
            "potential_dumpers": []
        }

def generate_pump_dump_report(token_address: str, token_data: dict, analysis_result: dict, token_tweets: list = None) -> str:
    """
    Generate a detailed report about a potential pump and dump scheme.
    
    Args:
        token_address: The token address being analyzed
        token_data: The detailed token data from get_detailed_token_transactions 
                  (contains metadata, holders_page_1, defi_activities_page_1, etc.)
        analysis_result: The result of the pump and dump analysis (including AI results)
        token_tweets: Optional list of tweets related to this token
        
    Returns:
        A detailed report string
    """
    
    # Extract key info from analysis_result
    is_pump_dump = analysis_result.get("is_pump_dump", False)
    confidence = analysis_result.get("confidence", 0)
    patterns = analysis_result.get("reasons", []) 
    metrics = analysis_result.get("volume_analysis", {})
    promoters = analysis_result.get("promoters", []) 
    ai_analysis = analysis_result.get("ai_analysis", {}) 
    
    # Extract data from token_data for reporting
    metadata = token_data.get('metadata', {})
    holders_page_1 = token_data.get('holders_page_1', [])
    defi_activities_page_1 = token_data.get('defi_activities_page_1', [])
    
    # Use AI confidence and summary if available, otherwise use heuristic
    report_confidence = ai_analysis.get('confidence', confidence)
    report_summary = ai_analysis.get('summary', "Analysis summary not available.")
    report_is_pump_dump = ai_analysis.get('is_pump_dump', is_pump_dump)
    
    # Create report file path
    clean_address = token_address.replace('/', '_').replace(':', '_')
    report_path = f"./data/reports/token_{clean_address}_report.txt"
    
    # --- Generate the report content --- 
    report = []
    report.append("=" * 80)
    report.append(f"PUMP AND DUMP ANALYSIS REPORT: {token_address}")
    report.append(f"ANALYSIS DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")
    
    # --- Summary Section --- 
    report.append("OVERALL ASSESSMENT")
    report.append("-" * 40)
    if report_is_pump_dump:
        report.append(f"⚠️ POTENTIAL PUMP AND DUMP DETECTED! (Confidence: {report_confidence:.2f})")
        report.append(f"   AI Summary: {report_summary}")
    else:
        report.append(f"No significant pump and dump pattern detected (Confidence: {report_confidence:.2f})")
        report.append(f"   AI Summary: {report_summary}")
    report.append("")

    # --- Token Metadata --- 
    report.append("TOKEN METADATA")
    report.append("-" * 40)
    if metadata:
        report.append(f"Name: {metadata.get('name', 'N/A')}")
        report.append(f"Symbol: {metadata.get('symbol', 'N/A')}")
        report.append(f"Decimals: {metadata.get('decimals', 'N/A')}")
        report.append(f"Total Supply: {metadata.get('supply', 'N/A')}")
        report.append(f"Holders (from meta): {metadata.get('holder', 'N/A')}")
        report.append(f"Mint Authority: {metadata.get('mint_authority', 'N/A')}")
        report.append(f"Freeze Authority: {metadata.get('freeze_authority', 'N/A')}")
    else:
        report.append("Metadata not available.")
    report.append("")

    # --- Holder Information (Sample) --- 
    report.append("HOLDER INFORMATION (Page 1 Sample)")
    report.append("-" * 40)
    if holders_page_1 and isinstance(holders_page_1, list): # Check it's a list
        report.append(f"Top {len(holders_page_1)} holders displayed (from page 1):")
        for i, holder in enumerate(holders_page_1[:10], 1): # Show top 10 from page 1
             owner = holder.get('owner', 'N/A')
             amount = holder.get('amount', 0)
             # Calculate percentage if supply and decimals are known
             supply_str = metadata.get('supply', '0')
             decimals_raw = metadata.get('decimals') # Get raw value without default
             percentage = "N/A" # Default to N/A
             formatted_amount_str = str(amount) # Default to raw amount string

             # Check if decimals is a valid number (int or float)
             decimals_valid = False
             if decimals_raw is not None:
                 try:
                     decimals = int(decimals_raw) # Try converting to int
                     decimals_valid = True
                 except (ValueError, TypeError):
                     # ... (rest of decimal validation logic remains the same) ...
                     pass # Keep decimals_valid as False for now

             # Format amount string if decimals are valid
             if decimals_valid:
                 try:
                     amount_int = int(amount)
                     formatted_amount = amount_int / (10**decimals)
                     # Format with reasonable precision, adjust as needed
                     formatted_amount_str = f"{formatted_amount:,.4f}" 
                 except (ValueError, TypeError):
                     formatted_amount_str = f"{amount} (Raw)" # Indicate raw if conversion fails

             # Proceed only if we have valid numbers for percentage
             if supply_str.isdigit() and decimals_valid:
                 try: 
                     supply = int(supply_str)
                     amount_int = int(amount)
                     percentage = f"{(amount_int / supply) * 100:.4f}%"
                 except (ValueError, TypeError) as calc_err:
                     logger.error(f"Error calculating percentage for holder {owner}: {calc_err}")
                     percentage = "N/A"
                         
             # Use the formatted amount string in the report line
             report.append(f" #{i}: {owner} (Amount: {formatted_amount_str}, Approx: {percentage})")
    elif holders_page_1: # It exists but is not a list
        report.append(f"Holder data received in unexpected format ({type(holders_page_1)}). Cannot display.")
    else:
        report.append("Holder data not available or empty.")
    report.append("")

    # --- Transaction Overview --- 
    report.append("TRANSACTION OVERVIEW")
    report.append("-" * 40)
    report.append(f"Total Transactions Analyzed: {token_data.get('total_transactions', 0)}")
    report.append(f"Buy Transactions (Heuristic): {token_data.get('buy_transactions', 0)}")
    report.append(f"Sell Transactions (Heuristic): {token_data.get('sell_transactions', 0)}")
    report.append(f"Unique Wallets Involved: {token_data.get('unique_wallets', 0)}")
    if "hourly_volumes" in token_data and token_data["hourly_volumes"]:
        hourly_volumes = token_data["hourly_volumes"]
        if hourly_volumes:
            peak_hour = max(hourly_volumes, key=hourly_volumes.get)
            peak_vol = hourly_volumes[peak_hour]
            report.append(f"Peak Hourly Volume: {peak_vol:.2f} around {datetime.fromtimestamp(float(peak_hour)).isoformat()}")
    report.append("")

    # --- Recent DeFi Activity (Sample) --- 
    report.append("RECENT DEFI ACTIVITY (Page 1 Sample)")
    report.append("-" * 40)
    if defi_activities_page_1 and isinstance(defi_activities_page_1, list): # Check it's a list
        report.append(f"Displaying {len(defi_activities_page_1)} recent activities:")
        for i, activity in enumerate(defi_activities_page_1[:10], 1): # Show top 10 from page 1
            ts = datetime.fromtimestamp(activity.get('block_time', 0)).strftime('%Y-%m-%d %H:%M:%S')
            act_type = activity.get('activity_type', 'Unknown')
            platform = activity.get('platform', ['Unknown'])[0]
            value = activity.get('value', 'N/A')
            from_addr = activity.get('from_address', 'N/A')
            # Safely format value as float if possible
            try: 
                value_str = f"${float(value):.2f}"
            except (ValueError, TypeError):
                value_str = f"{value}" # Display as is if not float
            report.append(f" #{i} {ts}: {act_type} via {platform} (From: {from_addr[:6]}..) (Value: {value_str}) ")
    elif defi_activities_page_1: # It exists but not a list
         report.append(f"DeFi activity data received in unexpected format ({type(defi_activities_page_1)}). Cannot display.")
    else:
        report.append("No recent DeFi activity data available.")
    report.append("")

    # --- AI Detailed Narrative --- 
    ai_narrative = ai_analysis.get("detailed_narrative", "AI analysis did not provide a detailed narrative.")
    report.append("AI ANALYSIS NARRATIVE")
    report.append("-" * 40)
    report.append(ai_narrative)
    report.append("")

    # --- Sample Related Tweets --- 
    if token_tweets:
        report.append("SAMPLE RELATED TWEETS (From Scan)")
        report.append("-" * 40)
        report.append(f"Found {len(token_tweets)} tweets mentioning the token (showing up to 5):")
        for i, tweet in enumerate(token_tweets[:5], 1):
            author = tweet.get('author', {}).get('userName', 'Unknown')
            text = tweet.get('text', 'N/A')
            created_at = tweet.get('created_at', 'N/A')
            url = tweet.get('url', '')
            report.append(f"\n Tweet #{i} by @{author} ({created_at})")
            report.append(f"   Text: {text[:200]}{'...' if len(text) > 200 else ''}")
            if url:
                report.append(f"   Link: {url}")
        report.append("")

    # --- Potential Dumpers (Identified by AI or Heuristic Fallback) --- 
    potential_dumpers_ai = ai_analysis.get("potential_dumpers", [])
    potential_dumpers_heuristic = analysis_result.get("potential_dumpers", [])
    
    # Reuse decimals validation logic from above if needed, or assume it's done
    # For simplicity here, let's re-check decimals (could be refactored)
    decimals_raw_dump = metadata.get('decimals') 
    decimals_valid_dump = False
    decimals_dump = 0
    if decimals_raw_dump is not None:
        try:
            decimals_dump = int(decimals_raw_dump)
            decimals_valid_dump = True
        except (ValueError, TypeError):
            pass # Ignore invalid decimals for dumpers amount formatting for now
            
    if potential_dumpers_ai:
        report.append("POTENTIAL DUMPERS (Identified by AI)")
        report.append("-" * 40)
        for dumper_addr in potential_dumpers_ai:
            report.append(f"- {dumper_addr}")
        report.append("")
    elif potential_dumpers_heuristic: # Fallback to heuristic if AI list is empty
        report.append("POTENTIAL DUMPERS (Identified by Heuristics)")
        report.append("-" * 40)
        # Display heuristic dumpers with more detail
        for i, dumper in enumerate(potential_dumpers_heuristic[:5], 1): # Show top 5 heuristic
            addr = dumper.get('address', 'N/A')
            sent_raw = dumper.get('sent', 0)
            received_raw = dumper.get('received', 0)
            ratio = dumper.get('dump_ratio', 0)
            
            # Format sent and received amounts
            sent_str = str(sent_raw)
            received_str = str(received_raw)
            if decimals_valid_dump:
                try:
                    sent_fmt = float(sent_raw) / (10**decimals_dump)
                    sent_str = f"{sent_fmt:,.4f}"
                except (ValueError, TypeError): pass # Keep raw string on error
                try:
                    rec_fmt = float(received_raw) / (10**decimals_dump)
                    received_str = f"{rec_fmt:,.4f}"
                except (ValueError, TypeError): pass # Keep raw string on error
            
            # Display full address instead of truncated
            report.append(f" #{i}: {addr} (Sent: {sent_str}, Received: {received_str}, Ratio: {ratio:.2f})")
        report.append("")
    
    # --- Heuristic Patterns Detected --- 
    if patterns:
        report.append("HEURISTIC PATTERNS DETECTED")
        report.append("-" * 40)
        for pattern in patterns:
            report.append(f"• {pattern}")
        report.append("")
    
    # --- Top Holders (Heuristic Analysis) --- 
    top_holders_heuristic = analysis_result.get("top_holders", [])
    
    # Reuse decimals validation logic again (could be refactored)
    decimals_raw_heur = metadata.get('decimals') 
    decimals_valid_heur = False
    decimals_heur = 0
    if decimals_raw_heur is not None:
        try:
            decimals_heur = int(decimals_raw_heur)
            decimals_valid_heur = True
        except (ValueError, TypeError):
            pass
            
    if top_holders_heuristic:
        report.append("TOP HOLDERS (Heuristic Analysis)")
        report.append("-" * 40)
        report.append("(Based on total received tokens during analysis window)") # Add context
        for i, holder in enumerate(top_holders_heuristic, 1):
             # Add the 'received' amount to the output
             address = holder.get('address', 'N/A')
             received_raw = holder.get('received', 'N/A') # Keep original key name
             percentage = holder.get('percent_of_supply', 0.0)
             
             # Format received amount
             received_str = str(received_raw)
             if decimals_valid_heur and received_raw != 'N/A':
                 try:
                     rec_fmt = float(received_raw) / (10**decimals_heur)
                     received_str = f"{rec_fmt:,.4f}"
                 except (ValueError, TypeError): pass # Keep raw string on error
                 
             report.append(f"#{i}: {address} (Received: {received_str}, Approx Holding: {percentage:.2f}%)")
        report.append("")

    # --- Twitter Promoters Section --- 
    if promoters:
        report.append("TWITTER PROMOTERS")
        report.append("-" * 40)
        report.append(f"Found {len(promoters)} Twitter accounts promoting this token")
        
        sorted_promoters = sorted(promoters, key=lambda x: x.get('influence_score', 0), reverse=True)
        for i, promoter in enumerate(sorted_promoters[:5], 1): # Show top 5
            username = promoter.get('username', 'unknown')
            followers = promoter.get('followers', 0)
            score = promoter.get('influence_score', 0)
            
            report.append(f"\n#{i}: @{username} (Followers: {followers}, Influence: {score:.2f})")
            if promoter.get('tweets'):
                sample_tweet = promoter['tweets'][0]
                tweet_text = sample_tweet.get('text', '')[:150]
                tweet_time = sample_tweet.get('date', '') # Key might be 'date' here
                report.append(f"   Sample Tweet ({tweet_time}): \"{tweet_text}...\"")
        report.append("")
    
    # --- Related Tweets Section --- 
    if token_tweets:
        report.append("RELATED TWEETS (Sample)")
        report.append("-" * 40)
        report.append(f"Found {len(token_tweets)} tweets mentioning this token")
        for i, tweet in enumerate(token_tweets[:5]): # Show sample
            author_data = tweet.get('author', {})
            username = author_data.get('userName', 'unknown')
            created_at = tweet.get('createdAt', 'unknown')
            text = tweet.get('text', 'No text')
            report.append(f"\nTweet {i+1}: @{username} ({created_at})")
            report.append(f"   Text: {text[:150]}...")
        report.append("")
    
    # --- Footer --- 
    report.append("=" * 80)
    report.append("NOTE: This is an automated analysis. Always conduct your own research.")
    report.append("=" * 80)
    
    # Join report lines and write to file
    report_content = "\n".join(report)
    
    # Ensure the reports directory exists
    os.makedirs("./data/reports", exist_ok=True)
    
    # Write the report to file
    with open(report_path, "w") as f:
        f.write(report_content)
    
    logger.info(f"Report saved to {report_path}")
    
    return report_content 