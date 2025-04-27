"""Main script to run the Solana social/on-chain monitor with pump-and-dump detection."""

import time
import logging
from datetime import datetime
import os
import sys
import argparse
from typing import List, Dict, Any

from config import settings
from social_aggregator import twitter
# from social_aggregator import telegram, discord # Uncomment when implemented
from onchain_monitor import solscan
from correlation_engine import engine
from correlation_engine import pump_dump_analyzer
from alerting import alert

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_monitor_cycle(test_mode=False):
    """Performs one cycle of fetching, analyzing, and alerting.
    
    Args:
        test_mode: If True, uses mock data instead of making API calls
    """
    logger.info("Starting new monitor cycle...")

    # 1. Fetch Social Data
    logger.info("--- Fetching Social Data ---")
    
    if test_mode:
        logger.info("TEST MODE: Using mock tweets")
        # Mock tweet data
        recent_tweets = [
            {
                "id": "1234567890",
                "text": "Check out this new Solana token! It's going to 100x for sure! 🚀🚀🚀 $SOL",
                "author_id": "12345",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "0987654321",
                "text": "BREAKING: New gem on Solana! Easy gains, don't miss out! Contract: AbCdEfGhIjKlMnOpQrStUvWxYz123456789ABCDEFG",
                "author_id": "67890",
                "created_at": datetime.now().isoformat()
            }
        ]
        logger.info(f"Loaded {len(recent_tweets)} mock tweets")
    else:
        # Fetch Twitter data - use the specialized function for pump-and-dump detection
        recent_tweets = twitter.search_pump_and_dump_tweets(
            since_minutes=settings.CORRELATION_TIME_WINDOW_MINUTES
        )
    
    if not recent_tweets:
        logger.warning("No tweets found. Skipping this monitoring cycle.")
        return
    
    # Quick scan for high-confidence pump indicators before AI analysis
    high_confidence_tweets = []
    for tweet in recent_tweets:
        text = tweet.get('text', '').lower()
        # Check for token contract address
        has_token_address = any(x in text.lower() for x in ["contract", "token address", "address:", "ca:"])
        # Check for pump indicators
        has_pump_indicators = any(x in text for x in ["100x", "1000x", "moonshot", "to the moon", "🚀"])
        # Check for urgency
        has_urgency = any(x in text.lower() for x in ["don't miss", "hurry", "last chance", "early"])
        
        score = 0
        if has_token_address:
            score += 0.4
        if has_pump_indicators:
            score += 0.3
        if has_urgency:
            score += 0.3
            
        if score >= 0.6:  # High confidence threshold
            author = tweet.get('author', {}).get('userName', 'Unknown')
            high_confidence_tweets.append({
                'author': author,
                'text': tweet.get('text'),
                'confidence': score,
                'url': tweet.get('url', '')
            })
    
    # Log summary of high-confidence tweets
    if high_confidence_tweets:
        logger.warning(f"Found {len(high_confidence_tweets)} high-confidence pump-and-dump tweets!")
        for i, t in enumerate(high_confidence_tweets[:3], 1):  # Show up to 3 examples
            logger.warning(f"High confidence tweet #{i}: @{t['author']} ({t['confidence']:.2f})")
            logger.warning(f"  {t['text'][:100]}..." if len(t['text']) > 100 else t['text'])

    # 2. Analyze Tweets with AI to extract sentiment and token addresses
    logger.info("--- Analyzing Tweets with AI ---")
    
    if test_mode:
        logger.info("TEST MODE: Using mock tweet analysis")
        # Mock tweet analysis results
        tweet_analysis = {
            "average_sentiment": 0.8,  # High pump score
            "positive_count": 2,
            "negative_count": 0,
            "neutral_count": 0,
            "potential_pump_tweets": [
                {
                    'tweet_id': recent_tweets[0]['id'],
                    'text': recent_tweets[0]['text'],
                    'author_id': recent_tweets[0]['author_id'],
                    'created_at': recent_tweets[0]['created_at'],
                    'pump_score': 0.9,
                    'sentiment': 'positive',
                    'extracted_addresses': [],
                    'rationale': 'Uses exaggerated claims (100x) and rocket emojis'
                },
                {
                    'tweet_id': recent_tweets[1]['id'],
                    'text': recent_tweets[1]['text'],
                    'author_id': recent_tweets[1]['author_id'],
                    'created_at': recent_tweets[1]['created_at'],
                    'pump_score': 0.85,
                    'sentiment': 'positive',
                    'extracted_addresses': ['AbCdEfGhIjKlMnOpQrStUvWxYz123456789ABCDEFG'],
                    'rationale': 'Uses urgent language ("don\'t miss out") and promises easy gains'
                }
            ],
            "extracted_addresses": ['AbCdEfGhIjKlMnOpQrStUvWxYz123456789ABCDEFG']
        }
    else:
        tweet_analysis = engine.analyze_tweet_with_ai(recent_tweets)
    
    # Extract addresses for on-chain analysis
    extracted_addresses = tweet_analysis.get("extracted_addresses", [])
    potential_pump_tweets = tweet_analysis.get("potential_pump_tweets", [])
    
    if not extracted_addresses and not potential_pump_tweets:
        logger.info("No token addresses extracted and no potential pump tweets found. Skipping on-chain analysis.")
        return
    
    # Log what we found
    logger.info(f"Found {len(extracted_addresses)} potential token addresses and {len(potential_pump_tweets)} potential pump tweets.")
    if extracted_addresses:
        logger.info(f"Extracted addresses: {', '.join(extracted_addresses[:5])}{' and more...' if len(extracted_addresses) > 5 else ''}")

    # 3. Fetch On-Chain Data
    logger.info("--- Fetching On-Chain Data ---")
    
    if test_mode:
        logger.info("TEST MODE: Using mock on-chain data")
        # Mock on-chain data
        all_onchain_transfers = [
            {
                "src": "Wallet1",
                "dst": "Wallet2",
                "amount": 1000.0,
                "blockTime": int(datetime.now().timestamp()) - 3600
            },
            {
                "src": "Wallet1",
                "dst": "Wallet3",
                "amount": 2000.0,
                "blockTime": int(datetime.now().timestamp()) - 1800
            },
            {
                "src": "Wallet2",
                "dst": "Wallet4",
                "amount": 500.0,
                "blockTime": int(datetime.now().timestamp()) - 900
            }
        ]
        logger.info(f"Loaded {len(all_onchain_transfers)} mock transfers")
    else:
        all_onchain_transfers = []
        
        # First check the extracted addresses (from tweets)
        for address in extracted_addresses:
            # Use the detailed transaction analysis for token addresses
            logger.info(f"Fetching detailed transaction data for token: {address}")
            token_data = solscan.get_detailed_token_transactions(address, hours_lookback=48)
            
            if token_data:
                # Save token address and related tweets for detailed analysis
                logger.info(f"Performing detailed pump and dump analysis for token: {address}")
                
                # Find tweets that mention this specific token
                token_tweets = []
                for tweet in recent_tweets:
                    if address.lower() in tweet.get('text', '').lower():
                        token_tweets.append(tweet)
                
                if token_tweets:
                    logger.info(f"Found {len(token_tweets)} tweets mentioning token {address}")
                
                # Run pump and dump analysis
                analysis_result = pump_dump_analyzer.analyze_token_transactions(token_data, token_tweets)
                
                # If it appears to be a pump and dump, generate a detailed report
                if analysis_result.get("is_pump_dump", False):
                    confidence = analysis_result.get("confidence", 0)
                    logger.warning(f"PUMP AND DUMP DETECTED for token {address} with {confidence:.2f} confidence")
                    
                    # Generate detailed report
                    report = pump_dump_analyzer.generate_pump_dump_report(address, token_data, analysis_result, token_tweets)
                    
                    # Also send an alert
                    subject = f"ALERT: Pump and Dump Detected for Token {address[:10]}..."
                    alert.send_alert(subject, report)
            
            # Also get standard transfers for correlation analysis
            token_transfers = solscan.get_token_transfers(address, limit=50)
            if token_transfers:
                logger.info(f"Found {len(token_transfers)} transfers for extracted token address: {address}")
                all_onchain_transfers.extend(token_transfers)
        
        # If no transfers found from extracted addresses, check the configured watch tokens
        if not all_onchain_transfers:
            for token_address in settings.SOLANA_WATCH_TOKENS:
                token_transfers = solscan.get_token_transfers(token_address, limit=50)
                if token_transfers:
                    logger.info(f"Found {len(token_transfers)} transfers for configured token: {token_address}")
                    all_onchain_transfers.extend(token_transfers)
    
    if not all_onchain_transfers:
        logger.warning("No on-chain transfers found for the extracted addresses or configured tokens. Skipping correlation.")
        return

    # 4. Analyze On-Chain Data
    logger.info("--- Analyzing On-Chain Data ---")
    
    if test_mode:
        logger.info("TEST MODE: Using mock on-chain analysis")
        # Mock on-chain analysis
        onchain_results = {
            "total_volume": 3500.0,
            "transfer_count": 3,
            "unique_senders": 2,
            "unique_receivers": 3,
            "unusual_patterns": [
                {
                    "type": "large_transfer",
                    "sender": "Wallet1",
                    "receiver": "Wallet3",
                    "amount": 2000.0,
                    "timestamp": int(datetime.now().timestamp()) - 1800
                },
                {
                    "type": "volume_spike",
                    "hour": int(datetime.now().timestamp()) // 3600,
                    "current_volume": 3000.0,
                    "previous_volume": 500.0,
                    "increase_factor": 6.0
                }
            ]
        }
    else:
        onchain_results = engine.analyze_onchain_activity(all_onchain_transfers, addresses=extracted_addresses)
    
    # 5. Find Correlations
    logger.info("--- Finding Correlations Using AI ---")
    
    if test_mode:
        logger.info("TEST MODE: Using mock correlation findings")
        # Mock correlation findings
        correlation_findings = [
            {
                "is_pump_and_dump": True,
                "confidence": 0.85,
                "description": "High confidence pump-and-dump scheme detected based on promotional language in tweets and unusual on-chain activity patterns.",
                "key_indicators": [
                    "Tweets using excessive hype (100x claims, rocket emojis)",
                    "Tweets containing urgent language (don't miss out)",
                    "Large token transfers observed shortly after promotional tweets",
                    "Significant volume spike (6x increase in short timeframe)"
                ]
            }
        ]
    else:
        correlation_findings = engine.correlate_with_ai(tweet_analysis, onchain_results)
    
    # 6. Send Alerts if Correlations Found
    if correlation_findings:
        high_confidence_findings = [f for f in correlation_findings 
                                 if f.get('confidence', 0) > 0.7 or 
                                    (f.get('is_pump_and_dump', False) and f.get('confidence', 0) > 0.5)]
        
        if high_confidence_findings:
            logger.warning(f"Detected {len(high_confidence_findings)} high-confidence pump-and-dump schemes. Sending alert...")
            
            # Format the findings into a message body
            subject = f"ALERT: Potential Pump-and-Dump Scheme Detected"
            message_body = f"Potential pump-and-dump scheme detected at {datetime.now()}:\n\n"
            
            for i, finding in enumerate(high_confidence_findings, 1):
                message_body += f"Finding #{i}:\n"
                message_body += f"- Confidence: {finding.get('confidence', 0):.2f}\n"
                message_body += f"- Description: {finding.get('description', 'No description provided')}\n"
                
                if 'key_indicators' in finding:
                    message_body += "- Key Indicators:\n"
                    for indicator in finding.get('key_indicators', []):
                        message_body += f"  * {indicator}\n"
                
                # Include sample tweet if available
                if potential_pump_tweets and i <= len(potential_pump_tweets):
                    message_body += f"\nSample suspicious tweet: \"{potential_pump_tweets[i-1].get('text', '')}\" (score: {potential_pump_tweets[i-1].get('pump_score', 0):.2f})\n"
                
                message_body += "\n"
            
            # Include summary of on-chain activity
            message_body += f"\nOn-Chain Activity Summary:\n"
            message_body += f"- Total transfers: {onchain_results.get('transfer_count', 0)}\n"
            message_body += f"- Total volume: {onchain_results.get('total_volume', 0):.2f}\n"
            message_body += f"- Unique senders: {onchain_results.get('unique_senders', 0)}\n"
            message_body += f"- Unique receivers: {onchain_results.get('unique_receivers', 0)}\n"
            message_body += f"- Unusual patterns detected: {len(onchain_results.get('unusual_patterns', []))}\n"
            
            # In test mode, just log the alert
            if test_mode:
                logger.info("TEST MODE: Alert would be sent with subject '%s'", subject)
                logger.info("TEST MODE: Alert message: %s", message_body)
            else:
                alert.send_alert(subject, message_body)
        else:
            logger.info("Correlations found but confidence too low for alert.")
    else:
        logger.info("No significant correlations detected in this cycle.")

    logger.info("Monitor cycle finished.")

def analyze_specific_token(token_address: str, scan_twitter: bool = True):
    """Performs a detailed analysis of a specific token address.
    
    This is useful for manual investigation of potential pump and dump schemes.
    
    Args:
        token_address: The token address to analyze
        scan_twitter: Whether to scan Twitter for tweets about this token
    """
    logger.info(f"Starting detailed analysis for token: {token_address}")
    
    # Delete existing report file for this token if it exists
    clean_address = token_address.replace('/', '_').replace(':', '_')
    report_path = f"./data/reports/token_{clean_address}_report.txt"
    if os.path.exists(report_path):
        try:
            os.remove(report_path)
            logger.info(f"Deleted existing report file: {report_path}")
        except OSError as e:
            logger.error(f"Error deleting existing report file {report_path}: {e}")
            
    # 1. Scan Twitter for mentions of this token (if requested)
    token_tweets = []
    if scan_twitter:
        logger.info("Scanning Twitter for mentions of this token...")
        
        # Search with the token address as keyword
        tweets = twitter.get_recent_tweets([token_address], since_minutes=1440)  # Look back 24 hours
        
        if tweets:
            logger.info(f"Found {len(tweets)} tweets mentioning token {token_address}")
            token_tweets = tweets
        else:
            logger.warning(f"No tweets found mentioning token {token_address}")
    
    # 2. Fetch and analyze on-chain data
    logger.info("Fetching detailed transaction data...")
    token_data = solscan.get_detailed_token_transactions(token_address, hours_lookback=72)  # 3 days of data
    
    if not token_data:
        logger.error(f"No transaction data found for token {token_address}")
        return
    
    # 3. Analyze for pump and dump patterns
    logger.info("Performing pump and dump analysis...")
    analysis_result = pump_dump_analyzer.analyze_token_transactions(token_data, token_tweets)
    
    # 4. If it's a potential pump and dump, find all Twitter promoters
    promoters = []
    if analysis_result.get("is_pump_dump", False) or analysis_result.get("confidence", 0) > 0.3:
        logger.info(f"Potential pump and dump detected. Finding Twitter promoters...")
        promoters = twitter.find_promoters_for_token(token_address, since_days=7)
        
        if promoters:
            logger.info(f"Found {len(promoters)} Twitter accounts promoting this token")
            # Include promoters in the analysis result for the report
            analysis_result["promoters"] = promoters
            
            # Log top promoters
            for i, promoter in enumerate(promoters[:3], 1):  # Top 3
                logger.warning(f"Top promoter #{i}: @{promoter['username']} - {promoter['followers']} followers, score: {promoter['influence_score']:.2f}")
                if promoter['tweets']:
                    logger.warning(f"  Sample tweet: {promoter['tweets'][0]['text'][:100]}...")
    
    # --- LOGGING ADDED FOR DEBUGGING --- 
    logger.info(f"[Debug] Tweets found for report: {len(token_tweets)}")
    logger.info(f"[Debug] Promoters found for report: {len(promoters)}")
    if token_tweets:
        logger.debug(f"[Debug] Sample tweet data for report: {token_tweets[0]}")
    if promoters:
        logger.debug(f"[Debug] Sample promoter data for report: {promoters[0]}")
    # --- END LOGGING ADDED --- 
        
    # 5. Generate and display report
    report = pump_dump_analyzer.generate_pump_dump_report(token_address, token_data, analysis_result, token_tweets)
    
    # 6. Log summary
    is_pump_dump = analysis_result.get("is_pump_dump", False)
    confidence = analysis_result.get("confidence", 0)
    
    if is_pump_dump:
        logger.warning(f"PUMP AND DUMP DETECTED with {confidence:.2f} confidence")
        if promoters:
            logger.warning(f"Found {len(promoters)} Twitter accounts promoting this token")
    else:
        logger.info(f"No pump and dump pattern detected (confidence: {confidence:.2f})")
    
    return analysis_result, report

def main():
    """Main loop to run the monitor periodically."""
    parser = argparse.ArgumentParser(description='Solana Pump-and-Dump Monitor')
    parser.add_argument('--test', action='store_true', help='Run in test mode with mock data (no API calls)')
    parser.add_argument('--once', action='store_true', help='Run one cycle and exit (don\'t loop)')
    parser.add_argument('--token', type=str, help='Analyze a specific token address and exit')
    args = parser.parse_args()
    
    # Create data directories if they don't exist
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./data/analysis", exist_ok=True)
    os.makedirs("./data/reports", exist_ok=True)
    
    # If analyzing a specific token
    if args.token:
        logger.info(f"Analyzing specific token: {args.token}")
        # When running from command line, we still want to save the report
        analysis_result, report_content = analyze_specific_token(args.token)
        if report_content:
            # Save the report manually here since the function doesn't save anymore
            try:
                clean_address = args.token.replace('/', '_').replace(':', '_')
                report_path = f"./data/reports/token_{clean_address}_report.txt"
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                with open(report_path, 'w') as f:
                    f.write(report_content)
                logger.info(f"Report saved to: {report_path}")
            except Exception as e:
                logger.error(f"Failed to save report for {args.token}: {e}")
        return 0
    
    logger.info("Starting Solana Pump-and-Dump Monitor")
    
    if args.test:
        logger.info("Running in TEST MODE with mock data (no API calls)")
    else:
        logger.info(f"Check interval: {settings.CHECK_INTERVAL_SECONDS} seconds")
        logger.info(f"Using specialized pump-and-dump keywords for Twitter search")
        logger.info(f"Using {settings.AI_MODEL} for analysis")
        
        # Check API keys
        missing_keys = []
        if settings.TWITTER_API_KEY == "YOUR_TWITTER_API_IO_KEY" or settings.TWITTER_API_KEY == "mock_twitter_key":
            missing_keys.append("Twitter API")
        if settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY" or settings.SOLSCAN_API_KEY == "mock_solscan_key":
            missing_keys.append("Solscan API")
        if settings.OPENAI_API_KEY == "YOUR_OPENAI_API_KEY" or settings.OPENAI_API_KEY == "mock_openai_key":
            missing_keys.append("OpenAI API")
        
        if missing_keys:
            logger.warning(f"Missing API keys: {', '.join(missing_keys)}. Please add them to your .env file.")
            logger.warning("Refer to env_example.txt for the format.")
            
            if not args.test:
                logger.error("Cannot run in normal mode without API keys. Use --test to run with mock data.")
                return 1

    try:
        if args.once:
            # Run one cycle and exit
            run_monitor_cycle(test_mode=args.test)
        else:
            # Run continuously
            while True:
                try:
                    run_monitor_cycle(test_mode=args.test)
                except Exception as e:
                    logger.exception("An error occurred during the monitor cycle", exc_info=e)
                
                if not args.test:
                    logger.info(f"Sleeping for {settings.CHECK_INTERVAL_SECONDS} seconds...")
                    time.sleep(settings.CHECK_INTERVAL_SECONDS)
                else:
                    # In test mode, we just run once and exit even without --once flag
                    logger.info("Test cycle completed. Exiting.")
                    break
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 