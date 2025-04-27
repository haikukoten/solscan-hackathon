# Solana Pump-and-Dump Detector

A comprehensive tool for detecting pump-and-dump schemes on the Solana blockchain by analyzing social media activity and on-chain transactions in real-time.

## Overview

The Solana Pump-and-Dump Detector is designed to identify potentially fraudulent token activity by correlating social media promotion with on-chain transaction patterns. The system continuously monitors Twitter for suspicious token mentions and analyzes corresponding token transactions to identify patterns indicative of pump-and-dump schemes.

Using both rule-based heuristics and AI-powered analysis (via OpenAI's models), this tool provides in-depth analysis of token behavior, holder distribution, wallet patterns, and social signals to identify potential scams before they can cause widespread financial harm.

## Key Features

- **Social Media Monitoring**: Scans Twitter for potential pump-and-dump related activity
- **On-Chain Analysis**: Fetches and analyzes token transaction data from Solscan
- **Contract Address Extraction**: Automatically identifies contract addresses mentioned in tweets
- **Advanced Transaction Pattern Analysis**: Identifies suspicious buying/selling patterns, volume spikes, and wallet behaviors
- **AI-Powered Detection**: Uses OpenAI's models to analyze both tweet content and transaction patterns
- **Comprehensive Reporting**: Generates detailed reports with transaction data, wallet analysis, and related tweets
- **Alerts System**: Configurable alerts when potential pump-and-dump schemes are detected
- **REST API**: Allows integration with other systems via a simple Flask API
- **Web Interface**: Simple HTML/CSS/JS frontend for manual token analysis

## Project Architecture

```
solscan-proj/
├── alerting/                  # Alert delivery systems (email, Telegram, Discord)
├── config/                    # Configuration files and settings
│   ├── settings.py            # Main configuration settings
│   └── pump_keywords.py       # Keywords for detecting pump-and-dump schemes
├── correlation_engine/        # Core analysis logic
│   ├── pump_dump_analyzer.py  # Main token analysis and pattern detection
│   └── engine.py              # Correlation between social and on-chain data
├── data/                      # Data storage directory
│   ├── analysis/              # Analysis results stored in JSON format
│   └── reports/               # Human-readable reports in text format
├── onchain_monitor/           # Solana blockchain monitoring modules
├── social_aggregator/         # Social media data collection modules
├── api.py                     # Flask REST API for token analysis
├── main.py                    # Main application entry point
├── requirements.txt           # Python dependencies
├── env_example.txt            # Example .env file with required variables
├── index.html                 # Simple web interface
├── style.css                  # CSS styles for the web interface
└── script.js                  # JavaScript for the web interface
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Git
- Access to Twitter API (for social media monitoring)
- Access to Solscan API (for on-chain data)
- OpenAI API key (optional, for enhanced AI analysis)

### Local Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/solana-pump-dump-detector.git
   cd solana-pump-dump-detector
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up API keys by creating a `.env` file in the project root (see env_example.txt):
   ```
   TWITTER_API_KEY=your_twitter_api_key
   SOLSCAN_API_KEY=your_solscan_api_key
   OPENAI_API_KEY=your_openai_api_key
   LOG_LEVEL=INFO
   # Additional optional settings
   ```

### Docker Installation

1. Build the Docker image:
   ```bash
   docker build -t solana-pump-dump-detector .
   ```

2. Create a `.env` file with your configuration

3. Run the container:
   ```bash
   docker run -d -p 5001:5001 -v ./data:/app/data --env-file .env solana-pump-dump-detector
   ```

## Usage

### Command Line Usage

#### Continuous Monitoring Mode

To run the monitor in continuous mode:

```bash
python main.py
```

This will scan Twitter, analyze tweets, look for contract addresses, fetch on-chain data, and detect pump-and-dump schemes according to the configured interval.

#### One-Time Scan

To run a single monitoring cycle:

```bash
python main.py --once
```

#### Analyze Specific Token

To perform a detailed analysis of a specific token:

```bash
python main.py --token TOKENADDRESS
```

Example:
```bash
python main.py --token 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
```

#### Advanced Options

The system supports several optional command-line arguments:

```bash
python main.py --token TOKENADDRESS --verbose --report-path ./custom_reports --no-ai
```

Options:
- `--verbose`: Enables detailed logging
- `--report-path PATH`: Specifies a custom path for report output
- `--no-ai`: Disables AI-powered analysis
- `--days DAYS`: Number of days of historical data to analyze (default: 7)
- `--config CONFIG`: Path to a custom configuration file

### API Usage

Start the API server:

```bash
python api.py
```

The API server will run on port 5001 by default. 

#### Analyzing a Token

To analyze a token, send a POST request to `/api/analyze`:

```bash
curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"token_address": "YOUR_TOKEN_ADDRESS"}'
```

Response format:
```json
{
  "token_address": "YOUR_TOKEN_ADDRESS",
  "is_pump_dump": true,
  "confidence": 0.85,
  "report_url": "http://localhost:5001/api/reports/token_YOUR_TOKEN_ADDRESS",
  "summary": "This token shows strong indications of being a pump and dump scheme...",
  "analysis_timestamp": "2023-05-01T12:34:56Z"
}
```

#### Retrieving a Report

To retrieve a previously generated report:

```bash
curl -X GET http://localhost:5001/api/reports/token_YOUR_TOKEN_ADDRESS
```

#### Batch Analysis

To analyze multiple tokens at once:

```bash
curl -X POST http://localhost:5001/api/analyze_batch \
  -H "Content-Type: application/json" \
  -d '{"token_addresses": ["TOKEN1", "TOKEN2", "TOKEN3"]}'
```

### Web Interface

Open `index.html` in your browser to use the simple web interface. Enter a token address in the provided field and click "Analyze" to generate a report.

For best results, serve the web interface using a local web server:

```bash
# Using Python's built-in HTTP server
python -m http.server
```

Then navigate to `http://localhost:8000` in your browser.

## Pump-and-Dump Detection Methodology

The system uses a multi-pronged approach to identify potential pump-and-dump schemes:

### Social Media Signals

- **Keyword Analysis**: Detects promotional language like "100x", "moon", "gem", etc.
- **Urgency Detection**: Identifies FOMO-inducing terms like "don't miss out", "last chance"
- **Sentiment Analysis**: Measures extreme positive sentiment paired with token mentions
- **Coordinated Promotion**: Detects multiple accounts promoting the same token in short timeframes

### On-Chain Signals

- **Volume Anomalies**: Identifies abnormal transaction volume spikes
- **Wallet Behavior Analysis**: 
  - Detects wallets with suspicious outflow patterns
  - Identifies "dumper" wallets selling large amounts after promotional activity
  - Analyzes wallet concentration to identify potential insider control
- **Buy/Sell Ratio**: Monitors for high sell-to-buy ratios shortly after promotional spikes
- **Token Distribution**: Examines how widely distributed the token is across wallets
- **Historical Patterns**: Compares current patterns with known pump-and-dump schemes

### AI Analysis

When an OpenAI API key is provided, the system leverages advanced AI models to:
- Perform deeper pattern analysis on transaction data
- Evaluate the semantic content of related tweets
- Generate narrative explanations and confidence scores
- Identify potential coordination between promoters and dumpers

## Configuration Options

Edit `config/settings.py` to customize various aspects of the detector:

- **API Keys**: Set your API keys for Twitter, Solscan, and OpenAI
- **Search Keywords**: Customize Twitter search terms to monitor
- **Time Windows**: Adjust correlation windows between social and on-chain activity
- **Alert Thresholds**: Set sensitivity levels for different detection triggers
- **Checking Intervals**: Change how frequently the system scans for new activity
- **Reporting Options**: Configure report format and detail level

## Output Files

The program generates several types of output files:

- **Transaction Data**: JSON files in `data/` containing raw transaction data
- **Analysis Results**: JSON files in `data/analysis/` containing detailed analysis of tokens
- **Reports**: Formatted text reports in `data/reports/` with comprehensive analysis

## Advanced Usage

### Custom Keyword Lists

You can customize the keywords used for detecting suspicious language in tweets:

1. Create a file called `custom_keywords.txt` in the project root
2. Add one keyword or phrase per line
3. Run with the custom keywords: `python main.py --keywords custom_keywords.txt`

### Integration with Other Systems

The API can be used to integrate with trading bots, monitoring systems, or dashboard applications:

```python
import requests
import json

def check_token(token_address):
    response = requests.post(
        "http://localhost:5001/api/analyze",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"token_address": token_address})
    )
    return response.json()

# Example usage
result = check_token("YOUR_TOKEN_ADDRESS")
if result["is_pump_dump"] and result["confidence"] > 0.7:
    # Take action (e.g., alert user, avoid trading)
    print(f"Warning: Potential pump and dump detected with {result['confidence']} confidence")
```

### Offline Mode

For situations with limited connectivity, use offline mode:

```bash
python main.py --offline --token TOKENADDRESS
```

In offline mode, the system will use cached data if available.

## Troubleshooting

### Common Issues

1. **API Key Authentication Failed**

   Problem: Logs show authentication errors when connecting to Twitter or Solscan.
   
   Solution: Verify your API keys are correct and properly formatted in the `.env` file.

2. **No Data for Some Tokens**

   Problem: Analysis returns with "Insufficient data" for certain tokens.
   
   Solution: Some newer or low-activity tokens may not have enough transactions for meaningful analysis. The default minimum is 10 transactions.

3. **Python Package Conflicts**

   Problem: Dependency errors during installation.
   
   Solution: Try installing in a fresh virtual environment with Python 3.9 for optimal compatibility.

4. **Web Interface Not Loading Data**

   Problem: The web interface loads but doesn't display analysis results.
   
   Solution: Check that the API server is running and accessible from your browser (CORS issues may occur).

## Contributing

We welcome contributions from the community! Here's how to contribute:

### Code Contributions

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

For development work, install additional dependencies:

```bash
pip install -r requirements-dev.txt
```

### Running Tests

Run the test suite to verify your changes:

```bash
pytest
```

### Coding Standards

We follow PEP 8 style guidelines. Please ensure your code is formatted accordingly:

```bash
black .
flake8
```

### Documentation

When adding new features, please update the relevant documentation:

- Update README.md for user-facing changes
- Update DOCUMENTATION.md for technical details
- Add docstrings to new functions and classes

## Community

- **Discord**: Join our community Discord server at [discord.gg/solana-pump-dump-detector](https://discord.gg/solana-pump-dump-detector)
- **Twitter**: Follow us at [@SolanaPumpWatch](https://twitter.com/SolanaPumpWatch)
- **Blog**: Visit our blog at [blog.solana-pump-dump-detector.com](https://blog.solana-pump-dump-detector.com)

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details. 