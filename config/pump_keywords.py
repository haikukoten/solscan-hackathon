"""Suggested keywords for detecting crypto pump-and-dump schemes on Twitter."""

# These keywords are grouped by category to help with updating or selecting specific types
# Feel free to uncomment/comment or add your own keywords based on your needs

# Basic Solana-related keywords
SOLANA_KEYWORDS = [
    "solana",
    "$SOL",
    "solana token",
    "sol token"
]

# Hype/Urgency indicators (strong pump signals)
HYPE_KEYWORDS = [
    "100x",
    "1000x",
    "to the moon",
    "mooning",
    "moonshot",
    "going parabolic",
    "next bitcoin",
    "next ethereum",
    "next solana",
    "don't miss out",
    "FOMO",
    "get in now",
    "early gem",
    "hidden gem",
    "easy gains",
    "guaranteed gains",
    "massive gains",
    "insane ROI",
    "rocket",
    "🚀", # Rocket emoji
]

# Presale/Launch keywords
PRESALE_KEYWORDS = [
    "presale",
    "pre-sale",
    "ICO",
    "IDO",
    "IEO",
    "fair launch",
    "stealth launch",
    "just launched",
    "launching soon",
    "low cap", 
    "low mcap",
    "micro cap",
]

# Suspicious promotional patterns
PROMO_KEYWORDS = [
    "shill",
    "airdrop",
    "free tokens",
    "influencer",
    "paid promotion",
    "not financial advice",
    "NFA",
    "dyor",
]

# Combine all keywords
def get_all_keywords():
    """Returns the full list of all suggested keywords."""
    all_keywords = []
    all_keywords.extend(SOLANA_KEYWORDS)
    all_keywords.extend(HYPE_KEYWORDS)
    all_keywords.extend(PRESALE_KEYWORDS)
    all_keywords.extend(PROMO_KEYWORDS)
    return all_keywords

# Combinations (more specific queries)
def get_combined_keywords():
    """Returns a list of combined keyword phrases (more specific)."""
    combined = []
    
    # Combine each Solana keyword with each hype keyword
    for sol_kw in SOLANA_KEYWORDS:
        for hype_kw in HYPE_KEYWORDS:
            combined.append(f"{sol_kw} {hype_kw}")
        
        for presale_kw in PRESALE_KEYWORDS:
            combined.append(f"{sol_kw} {presale_kw}")
    
    return combined

# High-precision keywords (best for limited API calls)
HIGH_PRECISION_KEYWORDS = [
    "solana 100x",
    "solana gem",
    "SOL moonshot",
    "solana presale rocket",
    "SOL token moon",
    "solana easy gains",
    "next SOL gem",
    "solana stealth launch",
    "SOL don't miss out",
    "solana massive gains"
]

# Combined keywords (generate more combinations)
COMBINED_KEYWORDS = [
    "solana incredible gains",
    "SOL to the moon",
    "next SOL winner",
    "solana pump",
    "SOL airdrop huge",
    "NOWK solana",  # Added the specific token that returned results
    "solana low cap gem",
    "SOL early investors",
    "solana hidden gem",
    "SOL pump soon"
]

def get_default_keywords():
    """Returns the default set of keywords for tracking pump-and-dumps."""
    combined = HIGH_PRECISION_KEYWORDS + COMBINED_KEYWORDS
    # Return unique keywords
    return list(set(combined))

if __name__ == "__main__":
    # Print out keyword stats when run directly
    all_kw = get_all_keywords()
    combined_kw = get_combined_keywords()
    default_kw = get_default_keywords()
    
    print(f"Total individual keywords: {len(all_kw)}")
    print(f"Total combined keywords: {len(combined_kw)}")
    print(f"Default keywords: {len(default_kw)}")
    print("\nExample default keywords to use:")
    for i, kw in enumerate(default_kw, 1):
        print(f"{i}. {kw}") 