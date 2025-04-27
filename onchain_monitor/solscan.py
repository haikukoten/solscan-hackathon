"""Handles fetching data from the Solscan Pro API."""

import requests
import logging
import time
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Update the API base URL to v2.0
SOLSCAN_API_BASE_URL = "https://pro-api.solscan.io/v2.0"

@retry(
    retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=lambda retry_state: logger.warning(
        f"Solscan API call failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _make_solscan_request(endpoint: str, params: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    """Makes an API request to Solscan with retry logic.
    
    Args:
        endpoint: The API endpoint to call.
        params: The query parameters to include.
        headers: Request headers including token.
        
    Returns:
        The JSON response data or empty dict on failure.
        
    Raises:
        Retries on RequestException or Timeout, gives up after 3 attempts.
    """
    url = SOLSCAN_API_BASE_URL + endpoint
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    return response.json()

def get_token_transfers(token_address: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetches recent transfers for a specific token.

    Args:
        token_address: The mint address of the token.
        limit: Maximum number of records to return (ignored by v2 endpoint, use page_size).
        offset: Number of records to skip (ignored by v2 endpoint, use page).

    Returns:
        A list of transfer records or an empty list on error.
    """
    if not settings.SOLSCAN_API_KEY or settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY":
        logger.warning("Solscan API key not configured. Skipping Solscan token transfer fetch.")
        return []

    # Use the correct endpoint for token-specific transfers
    endpoint = "/token/transfer"  
    headers = {"token": settings.SOLSCAN_API_KEY}
    
    # Calculate page and page_size based on limit/offset for compatibility
    # The page_size must be one of the allowed values: 10, 20, 30, 40, 60, 100
    allowed_page_sizes = [10, 20, 30, 40, 60, 100]
    if limit in allowed_page_sizes:
        page_size = limit
    else:
        page_size = 20 # Default page size
        
    page = (offset // page_size) + 1
    
    params = {
        "address": token_address,  # Use 'address' for the token address
        "page": page,
        "page_size": page_size
    }

    try:
        data = _make_solscan_request(endpoint, params, headers)
        transfers = data.get("data", [])
        logger.info(f"Fetched {len(transfers)} transfers for token: {token_address} (Page: {page}, Size: {page_size})")
        return transfers
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing Solscan token transfers: {e}")
        # Log response text if available for debugging
        if hasattr(e, 'response') and e.response:
             logger.error(f"Solscan Response: {e.response.text}")
        return []

def get_token_info(token_address: str) -> Dict[str, Any]:
    """Fetches information about a specific token.
    
    Args:
        token_address: The address of the token
        
    Returns:
        Dictionary with token details or empty dict if not found
    """
    if not settings.SOLSCAN_API_KEY or settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY":
        logger.warning("Solscan API key not configured. Skipping token info fetch.")
        return {}
    
    # Use token info endpoint to get basic details
    endpoint = "/token/meta"
    # Update to use token header
    headers = {"token": settings.SOLSCAN_API_KEY}
    params = {"address": token_address}
    
    try:
        return _make_solscan_request(endpoint, params, headers)
    except Exception as e:
        logger.error(f"Failed to fetch token info: {e}")
        return {}

def get_token_holders(token_address: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
    """Fetches the first page of token holders.
    
    Args:
        token_address: The address of the token
        page: Page number (default 1)
        page_size: Number of items per page (10, 20, 30, 40 allowed by API)
        
    Returns:
        List of holder records or empty list.
    """
    if not settings.SOLSCAN_API_KEY or settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY":
        logger.warning("Solscan API key not configured. Skipping token holders fetch.")
        return []
    
    endpoint = "/token/holders"
    headers = {"token": settings.SOLSCAN_API_KEY}
    
    allowed_page_sizes = [10, 20, 30, 40]
    if page_size not in allowed_page_sizes:
        page_size = 20 # Default
        
    params = {
        "address": token_address,
        "page": page,
        "page_size": page_size
    }
    
    try:
        data = _make_solscan_request(endpoint, params, headers)
        # Attempt to extract nested holder data from V2 response structure
        # Look for response['data']['items'] which seems to be the correct path
        holder_data_container = data.get("data", {})
        if isinstance(holder_data_container, dict):
            holders = holder_data_container.get("items", []) # *** Correct key is 'items' ***
        elif isinstance(holder_data_container, list): # Handle less likely case where it might be a direct list
             holders = holder_data_container
        else:
            holders = [] # Default to empty if structure is unexpected

        # Ensure we still have a list at the end
        if not isinstance(holders, list):
            logger.warning(f"Could not extract a list of holders from response. Path 'data.items' did not yield a list. Received structure: {type(data.get('data'))}. Defaulting to empty list.")
            holders = []
        else:
            logger.info(f"Fetched {len(holders)} holders for token: {token_address} (Page: {page})")

        return holders
    except Exception as e:
        logger.error(f"Failed to fetch token holders: {e}")
        if hasattr(e, 'response') and e.response:
             logger.error(f"Solscan Response: {e.response.text}")
        return []

def get_token_defi_activities(token_address: str, page: int = 1, page_size: int = 20, sort_by: str = "block_time", sort_order: str = "desc") -> List[Dict[str, Any]]:
    """Fetches DeFi activities involving a specific token.
    
    Args:
        token_address: The address of the token
        page: Page number for pagination
        page_size: Number of items per page (10, 20, 30, 40, 60, or 100)
        sort_by: Field to sort by (e.g. block_time)
        sort_order: Sort order (asc or desc)
        
    Returns:
        A list of DeFi activity records or an empty list on error.
    """
    if not settings.SOLSCAN_API_KEY or settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY":
        logger.warning("Solscan API key not configured. Skipping token DeFi activities fetch.")
        return []
    
    endpoint = "/token/defi/activities"
    headers = {"token": settings.SOLSCAN_API_KEY}
    
    # Validate page_size is one of the allowed values
    allowed_page_sizes = [10, 20, 30, 40, 60, 100]
    if page_size not in allowed_page_sizes:
        page_size = 20  # Use default if invalid
    
    # Build parameters
    params = {
        "address": token_address,
        "page": page,
        "page_size": page_size,
        "sort_by": sort_by,
        "sort_order": sort_order
    }
    
    try:
        data = _make_solscan_request(endpoint, params, headers)
        activities = data.get("data", [])
        logger.info(f"Fetched {len(activities)} DeFi activities for token: {token_address} (page {page})")
        return activities
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching token DeFi activities: {e}")
        return []

def get_detailed_token_transactions(token_address: str, hours_lookback: int = 24) -> Dict[str, Any]:
    """Fetches detailed transfers, metadata, holders, and defi activities for a token.
    
    Args:
        token_address: The mint address of the token
        hours_lookback: Hours to look back for transaction data (used for display/context, fetch gets all)
        
    Returns:
        A dictionary with combined token data
    """
    if not settings.SOLSCAN_API_KEY or settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY":
        logger.warning("Solscan API key not configured. Skipping detailed data fetch.")
        return {}
    
    # Create data directory if it doesn't exist
    os.makedirs("./data", exist_ok=True)
    clean_address = token_address.replace("/", "_").replace(":", "_")
    filename = f"./data/token_{clean_address}_detailed_data.json" # Changed filename
    
    # 1. Fetch Transfers (using pagination logic from before)
    logger.info(f"Fetching transfers for token: {token_address}")
    all_transfers = []
    max_transfers_fetch = 500  # Limit API calls
    page_size = 100 # Use max allowed for fewer calls
    page = 1
    while True:
        # NOTE: Using get_token_transfers which now uses the /token/transfer endpoint
        transfers_page = get_token_transfers(token_address, limit=page_size, offset=(page-1)*page_size)
        if not transfers_page:
            break
        all_transfers.extend(transfers_page)
        logger.info(f"Fetched batch of {len(transfers_page)} transfers (total so far: {len(all_transfers)})")
        if len(transfers_page) < page_size or len(all_transfers) >= max_transfers_fetch:
            break
        page += 1
        time.sleep(0.5) # Small delay 

    if not all_transfers:
        logger.warning(f"No transactions found for token: {token_address}")
        # Still try to fetch other data

    # 2. Fetch Token Metadata
    logger.info(f"Fetching metadata for token: {token_address}")
    token_info = get_token_info(token_address)
    time.sleep(0.5)

    # 3. Fetch Token Holders (First Page)
    logger.info(f"Fetching holders for token: {token_address}")
    token_holders = get_token_holders(token_address, page=1, page_size=20)
    if not isinstance(token_holders, list):
        logger.warning(f"Received unexpected type for token_holders: {type(token_holders)}. Defaulting to empty list.")
        token_holders = []
    time.sleep(0.5)

    # 4. Fetch Recent DeFi Activities (First Page)
    logger.info(f"Fetching recent DeFi activities for token: {token_address}")
    token_defi_activities = get_token_defi_activities(token_address, page=1, page_size=20)
    if not isinstance(token_defi_activities, list):
        logger.warning(f"Received unexpected type for token_defi_activities: {type(token_defi_activities)}. Defaulting to empty list.")
        token_defi_activities = []

    # Process transfers to get heuristic buy/sell/wallet counts (as before)
    buy_transactions_count = 0
    sell_transactions_count = 0
    wallets = {}
    hourly_volumes = {}
    for tx in all_transfers:
        # Simplified processing logic from before
        sender = tx.get("from_address", tx.get("src", "Unknown"))
        receiver = tx.get("to_address", tx.get("dst", "Unknown"))
        amount = float(tx.get("amount", 0))
        tx_time = tx.get("block_time", 0)
        tx_hour = datetime.fromtimestamp(tx_time).replace(minute=0, second=0).timestamp() if tx_time else 0
        
        if sender not in wallets: wallets[sender] = {"sent": 0, "received": 0}
        if receiver not in wallets: wallets[receiver] = {"sent": 0, "received": 0}
        wallets[sender]["sent"] += amount
        wallets[receiver]["received"] += amount
        if tx_hour not in hourly_volumes: hourly_volumes[tx_hour] = 0
        hourly_volumes[tx_hour] += amount
        if "exchange" in receiver.lower() or "swap" in receiver.lower() or "pool" in receiver.lower():
             sell_transactions_count += 1
        else:
             buy_transactions_count += 1

    # Combine all data
    result = {
        "token_address": token_address,
        "metadata": token_info.get("data", {}), # Store actual metadata
        "holders_page_1": token_holders, # Store first page of holders
        "defi_activities_page_1": token_defi_activities, # Store first page of defi activities
        "total_transactions": len(all_transfers),
        "buy_transactions": buy_transactions_count, # Heuristic count
        "sell_transactions": sell_transactions_count, # Heuristic count
        "unique_wallets": len(wallets),
        "hourly_volumes": hourly_volumes,
        "wallets": {addr: {**stats, "net": stats["received"] - stats["sent"]} for addr, stats in wallets.items()}, # Add net
        "raw_transactions": all_transfers[:50],  # Include a larger sample of raw txns
    }
    
    # Save combined results
    try:
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Saved detailed token data (transfers, meta, holders, defi) to {filename}")
    except Exception as e:
        logger.error(f"Failed to save detailed token data: {e}")
    
    return result

def get_account_transfers(account_address: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetches recent SOL transfers for a specific account.

    Args:
        account_address: The account address (wallet).
        limit: Maximum number of records to return.
        offset: Number of records to skip (for pagination).

    Returns:
        A list of transfer records or an empty list on error.
    """
    if not settings.SOLSCAN_API_KEY or settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY":
        logger.warning("Solscan API key not configured. Skipping Solscan account transfer fetch.")
        return []

    # Note: Adjust endpoint based on actual Solscan Pro API documentation for SOL transfers
    # This assumes an endpoint like /account/solTransfers - VERIFY THIS
    endpoint = f"/account/solTransfers" # <-- Verify endpoint name
    headers = {"token": settings.SOLSCAN_API_KEY}
    params = {
        "account": account_address,
        "limit": limit,
        "offset": offset
    }

    try:
        data = _make_solscan_request(endpoint, params, headers)
        transfers = data.get("data", []) # Assuming data is under a 'data' key
        logger.info(f"Fetched {len(transfers)} SOL transfers for account: {account_address}")
        return transfers
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"Endpoint {endpoint} not found. Verify Solscan API documentation for account SOL transfers.")
        logger.error(f"Error fetching account transfers from Solscan API for {account_address}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing Solscan account transfers: {e}")
        return []

def get_token_holder_stats(token_address: str) -> Dict[str, Any]:
    """Fetches token holder statistics.
    
    Args:
        token_address: The address of the token
        
    Returns:
        Dictionary with holder stats or empty dict if not found
    """
    if not settings.SOLSCAN_API_KEY or settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY":
        logger.warning("Solscan API key not configured. Skipping token holder stats fetch.")
        return {}
    
    endpoint = "/token/holders/statics"
    # Update to use token header
    headers = {"token": settings.SOLSCAN_API_KEY}
    params = {"address": token_address}
    
    try:
        return _make_solscan_request(endpoint, params, headers)
    except Exception as e:
        logger.error(f"Failed to fetch token holder stats: {e}")
        return {}

def get_account_transfer_export(account_address: str, 
                            token_address: str = None,
                            activity_types: List[str] = None,
                            from_time: int = None,
                            to_time: int = None,
                            exclude_amount_zero: bool = True,
                            flow: str = None) -> List[Dict[str, Any]]:
    """Exports transfer data for a specific account with various filtering options.
    
    Args:
        account_address: The Solana wallet address
        token_address: Optional filter by token address (use So11111111111111111111111111111111111111111 for native SOL)
        activity_types: Optional list of activity types to filter by (ACTIVITY_SPL_TRANSFER, ACTIVITY_SPL_BURN, etc.)
        from_time: Optional start time for filtering (Unix timestamp in seconds)
        to_time: Optional end time for filtering (Unix timestamp in seconds)
        exclude_amount_zero: Whether to exclude transfers with zero amount
        flow: Optional direction filter ('in' or 'out')
        
    Returns:
        A list of transfer records or an empty list on error.
    """
    if not settings.SOLSCAN_API_KEY or settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY":
        logger.warning("Solscan API key not configured. Skipping account transfer export.")
        return []
    
    endpoint = "/account/transfer/export"
    headers = {"token": settings.SOLSCAN_API_KEY}
    
    # Build parameters
    params = {"address": account_address}
    
    # Add optional parameters if provided
    if token_address:
        params["token"] = token_address
    
    if activity_types:
        params["activity_type"] = activity_types
    
    if from_time:
        params["from_time"] = from_time
    
    if to_time:
        params["to_time"] = to_time
    
    if exclude_amount_zero:
        params["exclude_amount_zero"] = exclude_amount_zero
    
    if flow and flow in ["in", "out"]:
        params["flow"] = flow
    
    try:
        data = _make_solscan_request(endpoint, params, headers)
        transfers = data.get("data", [])
        logger.info(f"Exported {len(transfers)} transfers for account: {account_address}")
        return transfers
    except Exception as e:
        logger.error(f"An unexpected error occurred while exporting account transfers: {e}")
        return []

def get_account_transfers_v2(account_address: str, 
                          exclude_amount_zero: bool = True,
                          page: int = 1,
                          page_size: int = 20) -> List[Dict[str, Any]]:
    """Fetches transfer data for a specific account/wallet.
    
    Args:
        account_address: The Solana wallet address
        exclude_amount_zero: Whether to exclude transfers with zero amount
        page: Page number for pagination
        page_size: Number of items per page (10, 20, 30, 40, 60, or 100)
        
    Returns:
        A list of transfer records or an empty list on error.
    """
    if not settings.SOLSCAN_API_KEY or settings.SOLSCAN_API_KEY == "YOUR_SOLSCAN_PRO_API_KEY":
        logger.warning("Solscan API key not configured. Skipping account transfer fetch.")
        return []
    
    endpoint = "/account/transfer"
    headers = {"token": settings.SOLSCAN_API_KEY}
    
    # Validate page_size is one of the allowed values
    allowed_page_sizes = [10, 20, 30, 40, 60, 100]
    if page_size not in allowed_page_sizes:
        page_size = 20  # Use default if invalid
    
    # Build parameters
    params = {
        "address": account_address,
        "page": page,
        "page_size": page_size
    }
    
    if exclude_amount_zero:
        params["exclude_amount_zero"] = exclude_amount_zero
    
    try:
        data = _make_solscan_request(endpoint, params, headers)
        transfers = data.get("data", [])
        logger.info(f"Fetched {len(transfers)} transfers for account: {account_address} (page {page})")
        return transfers
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching account transfers: {e}")
        return []

# Example usage (for testing)
if __name__ == '__main__':
    print("Testing Solscan fetch...")
    # Make sure to set a valid API key in config/settings.py first
    if settings.SOLSCAN_API_KEY != "YOUR_SOLSCAN_PRO_API_KEY":
        # Test token transfers (replace with a real token address)
        if settings.SOLANA_WATCH_TOKENS:
            test_token = settings.SOLANA_WATCH_TOKENS[0]
            print(f"\nTesting token transfers for: {test_token}")
            token_txs = get_token_transfers(test_token, limit=5)
            if token_txs:
                print(f"Successfully fetched {len(token_txs)} token transfers.")
                # print(f"First transfer: {token_txs[0]}")
            else:
                print("Failed to fetch token transfers or none found.")
        else:
            print("\nSkipping token transfer test, no SOLANA_WATCH_TOKENS in config.")

        # Test account transfers (replace with a real account address)
        if settings.SOLANA_WATCH_ADDRESSES:
            test_account = settings.SOLANA_WATCH_ADDRESSES[0]
            print(f"\nTesting account transfers for: {test_account}")
            # account_txs = get_account_transfers(test_account, limit=5)
            # if account_txs:
            #     print(f"Successfully fetched {len(account_txs)} account transfers.")
            #     # print(f"First transfer: {account_txs[0]}")
            # else:
            #     print("Failed to fetch account transfers or none found. Check endpoint name in code.")
            print("Account transfer test commented out - requires verifying correct endpoint.")
        else:
            print("\nSkipping account transfer test, no SOLANA_WATCH_ADDRESSES in config.")

    else:
        print("Skipping test, SOLSCAN_API_KEY not set in config/settings.py") 