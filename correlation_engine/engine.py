"""Correlation engine for analyzing social sentiment and on-chain activity."""

import logging
import re
import json
from typing import List, Dict, Any, Optional, Tuple
import openai

from config import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

def extract_solana_address(text: str) -> List[str]:
    """Extract potential Solana addresses from text using regex.
    
    Args:
        text: The text to analyze.
        
    Returns:
        A list of potential Solana addresses found in the text.
    """
    # Solana addresses are Base58 encoded and typically 32-44 characters
    # This is a basic regex and may need refinement
    solana_pattern = r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'
    addresses = re.findall(solana_pattern, text)
    return addresses

def analyze_tweet_with_ai(tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Uses GPT-4o-mini to **only extract Solana token addresses** from tweets.
    
    Args:
        tweets: A list of tweet objects from the Twitter API.
        
    Returns:
        A dictionary containing extracted addresses (sentiment/pump score fields will be defaults).
    """
    if not tweets:
        logger.warning("No tweets to analyze.")
        return {
            "average_sentiment": 0.0, 
            "positive_count": 0, 
            "negative_count": 0, 
            "neutral_count": 0,
            "potential_pump_tweets": [],
            "extracted_addresses": []
        }
    
    # Use fallback regex extraction if AI key is missing
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
        logger.warning("OpenAI API key not configured. Using regex for address extraction.")
        all_extracted_addresses = []
        for tweet in tweets:
            text = tweet.get('text', '')
            regex_addresses = extract_solana_address(text)
            if regex_addresses:
                all_extracted_addresses.extend(regex_addresses)
        unique_addresses = list(set(all_extracted_addresses))
        logger.info(f"Regex extraction found {len(unique_addresses)} unique potential addresses.")
        return {
            "average_sentiment": 0.0, 
            "positive_count": 0, 
            "negative_count": 0, 
            "neutral_count": 0,
            "potential_pump_tweets": [],
            "extracted_addresses": unique_addresses
        }
    
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Combined extraction results
    all_extracted_addresses = []
    
    # Process tweets in batches
    batch_size = 10 # Can likely use a larger batch now
    for i in range(0, len(tweets), batch_size):
        batch = tweets[i:i+batch_size]
        batch_texts = [tweet.get('text', '') for tweet in batch]
        
        # Simplified prompt for address extraction ONLY
        prompt = """
        Analyze the following tweets and extract ONLY the Solana token addresses (typically Base58 encoded strings of 32-44 characters) mentioned within them. Ignore any partial addresses or addresses from other blockchains.
        
        Return a single JSON object with one key: "extracted_addresses", which is an array of all unique Solana addresses found across all provided tweets.
        
        TWEETS:
        """
        
        for j, text in enumerate(batch_texts):
            prompt += f"\n\nTweet {j+1}: {text}"
        
        try:
            response = client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an AI assistant that extracts Solana token addresses from text. Provide the output as a JSON object containing an array under the key 'extracted_addresses'."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"} 
            )
            
            # Parse and process the AI response
            try:
                analysis = json.loads(response.choices[0].message.content)
                addresses = analysis.get('extracted_addresses', [])
                if addresses:
                    all_extracted_addresses.extend(addresses)
                
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Error parsing AI response for address extraction: {e}")
                # Fallback: use regex for this batch
                for text in batch_texts:
                    regex_addresses = extract_solana_address(text)
                    if regex_addresses:
                        all_extracted_addresses.extend(regex_addresses)
                        
        except Exception as e:
            logger.error(f"Error using OpenAI API for address extraction: {e}")
            # Fallback: use regex for this batch
            for text in batch_texts:
                regex_addresses = extract_solana_address(text)
                if regex_addresses:
                    all_extracted_addresses.extend(regex_addresses)
    
    # Deduplicate addresses
    unique_addresses = list(set(all_extracted_addresses))
    
    logger.info(f"Address extraction complete: Found {len(unique_addresses)} unique potential addresses.")
    
    # Return the expected structure, but with defaults for non-extraction fields
    return {
        "average_sentiment": 0.0,
        "positive_count": 0,
        "negative_count": 0,
        "neutral_count": 0,
        "potential_pump_tweets": [],
        "extracted_addresses": unique_addresses
    }

def analyze_onchain_activity(transfers: List[Dict[str, Any]], addresses: List[str]=None) -> Dict[str, Any]:
    """Analyzes on-chain activity from a list of transfers, focusing on potential pump and dump patterns.
    
    Args:
        transfers: A list of transfer objects from Solscan.
        addresses: Optional list of addresses to specifically analyze.
        
    Returns:
        A dictionary containing activity analysis results.
    """
    if not transfers:
        return {
            "total_volume": 0.0, 
            "transfer_count": 0, 
            "unique_senders": 0, 
            "unique_receivers": 0,
            "unusual_patterns": []
        }

    logger.info(f"Analyzing on-chain activity for {len(transfers)} transfers...")
    
    # Basic metrics
    transfer_count = len(transfers)
    
    # Initialize placeholders for metrics we'll try to extract
    total_volume = 0.0
    senders = set()
    receivers = set()
    unusual_patterns = []
    
    # Track time-based patterns (needs actual timestamps in the transfers)
    # This would be more robust in a real implementation
    volume_by_hour = {}
    
    for tx in transfers:
        # Extract basic info - you'll need to adjust based on actual Solscan response format
        try:
            # Example fields - adjust based on actual Solscan response format
            sender = tx.get('src', tx.get('from', ''))
            receiver = tx.get('dst', tx.get('to', ''))
            amount = float(tx.get('amount', tx.get('lamport', 0)))
            timestamp = tx.get('blockTime', 0)  # Unix timestamp
            
            # Add to basic metrics
            total_volume += amount
            if sender:
                senders.add(sender)
            if receiver:
                receivers.add(receiver)
                
            # Group by hour for trend analysis
            hour = timestamp // 3600  # Convert to hours
            volume_by_hour[hour] = volume_by_hour.get(hour, 0) + amount
            
            # Look for large transfers - potential dumps
            if amount > 1000:  # Adjust threshold as needed
                unusual_patterns.append({
                    'type': 'large_transfer',
                    'sender': sender,
                    'receiver': receiver,
                    'amount': amount,
                    'timestamp': timestamp
                })
                
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing transfer data: {e}")
    
    # Analyze for volume spikes - this is simplistic, would be more robust with historical data
    if len(volume_by_hour) > 1:
        hours = sorted(volume_by_hour.keys())
        for i in range(1, len(hours)):
            curr_vol = volume_by_hour[hours[i]]
            prev_vol = volume_by_hour[hours[i-1]]
            if prev_vol > 0 and curr_vol / prev_vol > settings.VOLUME_SPIKE_THRESHOLD_PERCENT / 100:
                unusual_patterns.append({
                    'type': 'volume_spike',
                    'hour': hours[i],
                    'current_volume': curr_vol,
                    'previous_volume': prev_vol,
                    'increase_factor': curr_vol / prev_vol
                })
    
    logger.info(f"On-chain analysis complete: Count={transfer_count}, Volume={total_volume:.2f}, Senders={len(senders)}, Receivers={len(receivers)}, Unusual patterns={len(unusual_patterns)}")
    
    return {
        "total_volume": total_volume,
        "transfer_count": transfer_count,
        "unique_senders": len(senders),
        "unique_receivers": len(receivers),
        "unusual_patterns": unusual_patterns
    }

def correlate_with_ai(tweet_analysis: Dict[str, Any], onchain_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Uses GPT-4o-mini to correlate social sentiment with on-chain activity to detect pump and dump schemes.
    
    Args:
        tweet_analysis: Results from analyze_tweet_with_ai.
        onchain_analysis: Results from analyze_onchain_activity.
        
    Returns:
        A list of correlation findings, with confidence scores and details.
    """
    if not tweet_analysis.get("potential_pump_tweets") or not onchain_analysis.get("transfer_count"):
        logger.info("Insufficient data for correlation analysis.")
        return []
    
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
        logger.warning("OpenAI API key not configured. Using simplified correlation logic.")
        # Fall back to simpler heuristics
        correlations = []
        
        # Simple rule: If high sentiment and unusual patterns detected
        if (tweet_analysis.get("average_sentiment", 0) > settings.SENTIMENT_SPIKE_THRESHOLD and 
            len(onchain_analysis.get("unusual_patterns", [])) > 0):
            
            correlation_description = (
                f"Potential pump and dump: High pump-scheme indicators in tweets (score: {tweet_analysis['average_sentiment']:.2f}) "
                f"coinciding with unusual on-chain activity ({len(onchain_analysis['unusual_patterns'])} patterns detected)."
            )
            logger.warning(correlation_description)
            correlations.append({
                "description": correlation_description,
                "confidence": 0.7,  # Dummy confidence
                "tweet_indicators": {"average_sentiment": tweet_analysis["average_sentiment"]},
                "onchain_indicators": {"unusual_patterns": len(onchain_analysis["unusual_patterns"])}
            })
            
        return correlations
    
    # If we have OpenAI API key, use GPT-4o-mini for correlation
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Prepare the data for the AI prompt
    tweet_data = {
        "average_pump_score": tweet_analysis.get("average_sentiment", 0),
        "potential_pump_tweets_count": len(tweet_analysis.get("potential_pump_tweets", [])),
        "potential_pump_tweets_samples": tweet_analysis.get("potential_pump_tweets", [])[:3],  # Limit to 3 samples for prompt size
        "extracted_addresses_count": len(tweet_analysis.get("extracted_addresses", [])),
        "extracted_addresses_samples": tweet_analysis.get("extracted_addresses", [])[:5]  # Limit to 5 samples for prompt size
    }
    
    onchain_data = {
        "total_volume": onchain_analysis.get("total_volume", 0),
        "transfer_count": onchain_analysis.get("transfer_count", 0),
        "unique_senders": onchain_analysis.get("unique_senders", 0),
        "unique_receivers": onchain_analysis.get("unique_receivers", 0),
        "unusual_patterns_count": len(onchain_analysis.get("unusual_patterns", [])),
        "unusual_patterns_samples": onchain_analysis.get("unusual_patterns", [])[:3]  # Limit to 3 samples for prompt size
    }
    
    prompt = f"""
    Analyze this combined social media and blockchain data to identify potential pump and dump schemes.
    
    SOCIAL MEDIA DATA:
    - Average pump scheme indicator score: {tweet_data['average_pump_score']:.2f} (0-1 scale, higher is more concerning)
    - Number of tweets with high pump scheme indicators: {tweet_data['potential_pump_tweets_count']}
    - Number of unique token addresses extracted: {tweet_data['extracted_addresses_count']}
    
    Sample tweets with high pump indicators:
    {json.dumps(tweet_data['potential_pump_tweets_samples'], indent=2)}
    
    Sample extracted token addresses:
    {tweet_data['extracted_addresses_samples']}
    
    BLOCKCHAIN DATA:
    - Total transaction volume: {onchain_data['total_volume']}
    - Number of transfers: {onchain_data['transfer_count']}
    - Unique senders: {onchain_data['unique_senders']}
    - Unique receivers: {onchain_data['unique_receivers']}
    - Number of unusual patterns detected: {onchain_data['unusual_patterns_count']}
    
    Sample unusual patterns:
    {json.dumps(onchain_data['unusual_patterns_samples'], indent=2)}
    
    Based on this data, determine if there is evidence of a pump and dump scheme. Consider:
    1. High social media hype coinciding with unusual trading patterns
    2. Promises of huge returns paired with concentrated selling
    3. Urgency in social messages paired with volume spikes
    4. Other suspicious correlations
    
    Return a JSON array of findings with these fields:
    - "is_pump_and_dump": boolean (true if likely a pump and dump)
    - "confidence": number (0-1 scale)
    - "description": string (explanation of finding)
    - "key_indicators": array of strings (list the most important indicators)
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a cryptocurrency fraud detection expert that analyzes social media and blockchain data to identify pump and dump schemes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=800
        )
        
        try:
            analysis = json.loads(response.choices[0].message.content)
            findings = analysis.get('findings', [])
            
            # Log and return findings
            for finding in findings:
                if finding.get('is_pump_and_dump', False) and finding.get('confidence', 0) > 0.5:
                    logger.warning(f"AI detected potential pump and dump: {finding.get('description')} (confidence: {finding.get('confidence'):.2f})")
                else:
                    logger.info(f"AI correlation finding: {finding.get('description')} (confidence: {finding.get('confidence'):.2f})")
            
            return findings
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Error parsing AI correlation response: {e}")
            return []
            
    except Exception as e:
        logger.error(f"Error using OpenAI API for correlation: {e}")
        return []

def find_correlations(sentiment_data: Dict[str, Any], onchain_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Legacy function - now serves as wrapper around correlate_with_ai to maintain compatibility.
    
    Args:
        sentiment_data: Results from analyze_sentiment or analyze_tweet_with_ai.
        onchain_data: Results from analyze_onchain_activity.
        
    Returns:
        A list of correlation findings.
    """
    # For backwards compatibility, check if this is the old format or new format
    if "potential_pump_tweets" in sentiment_data:
        # New format, use correlate_with_ai
        return correlate_with_ai(sentiment_data, onchain_data)
    else:
        # Old format, use the simplified logic
        logger.info("Using simplified correlation logic (legacy format detected).")
        correlations = []
        
        sentiment_threshold = settings.SENTIMENT_SPIKE_THRESHOLD
        if sentiment_data.get("average_sentiment", 0) > sentiment_threshold and onchain_data.get("transfer_count", 0) > 10:
            correlation_description = (
                f"Potential correlation: High positive sentiment (avg: {sentiment_data['average_sentiment']:.2f}) "
                f"coinciding with on-chain activity (transfers: {onchain_data['transfer_count']})."
            )
            logger.warning(correlation_description)
            correlations.append({
                "description": correlation_description,
                "confidence": 0.6,
                "legacy_format": True
            })
            
        return correlations

# Legacy function - kept for backward compatibility
def analyze_sentiment(tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Legacy function for backward compatibility - delegates to analyze_tweet_with_ai
    
    Args:
        tweets: A list of tweet objects.
        
    Returns:
        A dictionary containing sentiment analysis results.
    """
    logger.info("Using analyze_tweet_with_ai for sentiment analysis.")
    ai_results = analyze_tweet_with_ai(tweets)
    
    # Return in the format expected by legacy code
    return {
        "average_sentiment": ai_results["average_sentiment"],
        "positive_count": ai_results["positive_count"],
        "negative_count": ai_results["negative_count"],
        "neutral_count": ai_results["neutral_count"]
    } 