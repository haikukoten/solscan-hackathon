"""Handles fetching data from twitterapi.io."""

import requests
import random
import logging
import time
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import os

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

TWITTER_API_BASE_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"

@retry(
    retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=lambda retry_state: logger.warning(
        f"API call failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _fetch_tweets_with_retry(keyword: str, since_str: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Makes API requests to Twitter with retry logic.
    
    Args:
        keyword: The keyword to search for.
        since_str: The 'since' parameter formatted as a string.
        headers: Request headers including API key.
        
    Returns:
        A list of tweet objects or empty list on failure.
        
    Raises:
        Retries on RequestException or Timeout, gives up after 3 attempts.
    """
    # Use queryType=Latest as this is known to work with the API
    params = {
        "queryType": "Latest", 
        "query": keyword
    }
    
    response = requests.get(TWITTER_API_BASE_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    return data.get("tweets", [])

def get_recent_tweets(keywords: List[str], since_minutes: int = 60) -> List[Dict[str, Any]]:
    """Fetches recent tweets containing specified keywords using twitterapi.io.

    Args:
        keywords: A list of keywords to search for.
        since_minutes: How many minutes back to search.

    Returns:
        A list of tweets (dictionaries) or an empty list if an error occurs or no tweets are found.
    """
    if not settings.TWITTER_API_KEY or settings.TWITTER_API_KEY == "YOUR_TWITTER_API_IO_KEY":
        logger.warning("Twitter API key not configured. Skipping Twitter fetch.")
        return []

    headers = {
        "X-API-Key": settings.TWITTER_API_KEY,
        "User-Agent": random.choice(settings.TWITTER_USER_AGENTS) # Rotate user agents
    }

    # Calculate the 'since' timestamp
    since_time = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    since_str = since_time.strftime("%Y-%m-%d_%H:%M:%S_UTC")
    
    all_tweets = []
    
    # For pump-and-dump detection, we're better off making separate API calls for different keywords
    # rather than using OR, to ensure we get relevant results for each keyword
    for keyword in keywords[:10]:  # Limit to first 10 keywords to avoid too many API calls
        logger.info(f"Searching for keyword: {keyword}")
        
        try:
            tweets = _fetch_tweets_with_retry(keyword, since_str, headers)
            
            # Skip duplicates (same tweet ID)
            existing_ids = {t.get('id') for t in all_tweets}
            new_tweets = [t for t in tweets if t.get('id') not in existing_ids]
            
            all_tweets.extend(new_tweets)
            logger.info(f"Fetched {len(new_tweets)} new tweets for keyword: {keyword}")
            
            # Log sample tweets for this keyword
            if new_tweets:
                sample_size = min(2, len(new_tweets))  # Log up to 2 sample tweets
                logger.info(f"Sample tweets for '{keyword}':")
                for i, tweet in enumerate(new_tweets[:sample_size]):
                    author = tweet.get('author', {}).get('userName', 'Unknown')
                    created_at = tweet.get('createdAt', 'Unknown date')
                    text = tweet.get('text', 'No text')
                    # Truncate long tweet text for logging
                    truncated_text = text[:100] + "..." if len(text) > 100 else text
                    logger.info(f"  Tweet {i+1}: @{author} - {created_at}")
                    logger.info(f"    {truncated_text}")
                    
                    # If there are token addresses or other interesting mentions, log those separately
                    if "token address" in text.lower() or "contract" in text.lower():
                        logger.info(f"    [POTENTIAL TOKEN ADDRESS FOUND in tweet from @{author}]")
                    
                    # Look for rocket emojis, "100x", etc. as indicators of potential pump schemes
                    if "🚀" in text or "100x" in text or "1000x" in text or "to the moon" in text.lower():
                        logger.info(f"    [PUMP INDICATORS FOUND in tweet from @{author}]")

            # Handle rate limiting
            if len(all_tweets) >= 100:  # Cap at 100 total tweets
                logger.info(f"Reached maximum tweet count (100). Stopping search.")
                break
                
            # Small delay between requests to avoid rate limiting
            if keyword != keywords[:10][-1]:  # Don't sleep after the last keyword
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing tweets for '{keyword}': {e}")
            # Continue with other keywords
    
    logger.info(f"Total unique tweets fetched: {len(all_tweets)}")
    return all_tweets

def find_promoters_for_token(token_address: str, since_days: int = 7) -> List[Dict[str, Any]]:
    """Searches Twitter for all accounts that promoted a specific token address.
    
    Args:
        token_address: The token address to search for
        since_days: How many days back to search
        
    Returns:
        A list of dictionaries containing promoter info, sorted by influence
    """
    if not settings.TWITTER_API_KEY or settings.TWITTER_API_KEY == "YOUR_TWITTER_API_IO_KEY":
        logger.warning("Twitter API key not configured. Skipping Twitter promoter search.")
        return []
    
    logger.info(f"Searching for Twitter accounts promoting token: {token_address}")
    
    # Check several variations of how people might post the address
    search_terms = [
        token_address,                        # Raw address
        f"contract {token_address[:8]}",      # Contract + first part
        f"CA: {token_address[:8]}",           # CA: + first part
        f"address: {token_address[:8]}"       # address: + first part
    ]
    
    # Fetch tweets containing references to this token address
    since_minutes = since_days * 24 * 60  # Convert days to minutes
    promotion_tweets = get_recent_tweets(search_terms, since_minutes=since_minutes)
    
    if not promotion_tweets:
        logger.warning(f"No tweets found promoting token: {token_address}")
        return []
    
    logger.info(f"Found {len(promotion_tweets)} tweets mentioning token: {token_address}")
    
    # Analyze promoters (Twitter accounts)
    promoters = {}
    
    for tweet in promotion_tweets:
        author_data = tweet.get('author', {})
        username = author_data.get('userName', 'Unknown')
        
        if username not in promoters:
            # Extract account details
            promoters[username] = {
                'username': username,
                'display_name': author_data.get('name', 'Unknown'),
                'followers': author_data.get('followers', 0),
                'creation_date': author_data.get('createdAt', 'Unknown'),
                'is_verified': author_data.get('isVerified', False),
                'tweets': [],
                'pump_indicators': 0,
                'influence_score': 0.0
            }
        
        # Add tweet to this promoter's list
        tweet_text = tweet.get('text', '')
        tweet_date = tweet.get('createdAt', 'Unknown')
        tweet_url = tweet.get('url', '')
        
        promoters[username]['tweets'].append({
            'text': tweet_text,
            'date': tweet_date,
            'url': tweet_url
        })
        
        # Calculate a "pump indicator" score based on content
        if "100x" in tweet_text or "1000x" in tweet_text:
            promoters[username]['pump_indicators'] += 3
        if "🚀" in tweet_text:
            promoters[username]['pump_indicators'] += 2
        if "moon" in tweet_text.lower():
            promoters[username]['pump_indicators'] += 2
        if "gem" in tweet_text.lower():
            promoters[username]['pump_indicators'] += 1
        if "early" in tweet_text.lower():
            promoters[username]['pump_indicators'] += 1
        if "don't miss" in tweet_text.lower() or "hurry" in tweet_text.lower():
            promoters[username]['pump_indicators'] += 3
    
    # Calculate influence score for each promoter
    for username, data in promoters.items():
        # Base influence on follower count (logarithmic scale to prevent massive accounts from dominating)
        follower_factor = min(10, max(1, (data['followers'] + 1) // 100))
        
        # Combine with pump indicators
        promoters[username]['influence_score'] = (data['pump_indicators'] * follower_factor) / 10
    
    # Convert to list and sort by influence score
    promoter_list = list(promoters.values())
    promoter_list.sort(key=lambda x: x['influence_score'], reverse=True)
    
    # Save results to JSON for reference
    try:
        clean_address = token_address.replace("/", "_").replace(":", "_")
        os.makedirs("./data/twitter", exist_ok=True)
        
        with open(f"./data/twitter/token_{clean_address}_promoters.json", 'w') as f:
            json.dump(promoter_list, f, indent=2)
        logger.info(f"Saved promoter data to data/twitter/token_{clean_address}_promoters.json")
    except Exception as e:
        logger.error(f"Error saving promoter data: {e}")
    
    return promoter_list

def search_pump_and_dump_tweets(since_minutes: int = 60) -> List[Dict[str, Any]]:
    """Specialized function for searching tweets that might indicate pump-and-dump schemes.
    
    This uses the keywords defined in settings specifically targeting pump-and-dump language.
    
    Args:
        since_minutes: How many minutes back to search.
        
    Returns:
        A list of tweets that might be related to pump-and-dump schemes.
    """
    return get_recent_tweets(settings.TWITTER_KEYWORDS, since_minutes)

# Example usage (for testing)
if __name__ == '__main__':
    print("Testing Twitter fetch for pump-and-dump detection...")
    # Make sure to set a valid API key in config/settings.py first
    if settings.TWITTER_API_KEY != "YOUR_TWITTER_API_IO_KEY":
        print(f"Using {len(settings.TWITTER_KEYWORDS)} pump-and-dump related keywords")
        print(f"First few keywords: {settings.TWITTER_KEYWORDS[:5]}")
        
        recent_tweets = search_pump_and_dump_tweets(since_minutes=120)
        if recent_tweets:
            print(f"Successfully fetched {len(recent_tweets)} potential pump-and-dump related tweets.")
            # Print a sample tweet
            if len(recent_tweets) > 0:
                sample = recent_tweets[0]
                print("\nSample tweet:")
                print(f"ID: {sample.get('id')}")
                print(f"Text: {sample.get('text')}")
                print(f"Author: {sample.get('author', {}).get('userName', 'Unknown')}")
                print(f"Created: {sample.get('createdAt')}")
        else:
            print("Failed to fetch tweets or no tweets found.")
    else:
        print("Skipping test, TWITTER_API_KEY not set in config/settings.py") 