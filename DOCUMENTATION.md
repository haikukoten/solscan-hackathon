# Solana Pump-and-Dump Detector Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
   - [Pump and Dump Analyzer](#pump-and-dump-analyzer)
   - [Social Media Aggregator](#social-media-aggregator)
   - [On-chain Monitor](#on-chain-monitor)
   - [Correlation Engine](#correlation-engine)
   - [Alerting System](#alerting-system)
4. [API Reference](#api-reference)
5. [Configuration Guide](#configuration-guide)
6. [Implementation Details](#implementation-details)
7. [Deployment Guide](#deployment-guide)
8. [Troubleshooting](#troubleshooting)

## Introduction

The Solana Pump-and-Dump Detector is a comprehensive system designed to identify and analyze potential pump-and-dump schemes on the Solana blockchain. Pump-and-dump schemes typically involve coordinated efforts to artificially inflate a token's price through misleading promotion (the "pump") followed by a mass sell-off (the "dump") when prices peak, leaving most investors with significant losses.

This system combines on-chain transaction data analysis with social media monitoring to detect patterns associated with such schemes. It provides detailed analysis including transaction graphs, wallet behavior patterns, social sentiment analysis, and AI-powered evaluation to generate comprehensive reports on tokens of interest.

## System Architecture

The system follows a modular architecture with several interconnected components:

```
                                 ┌─────────────────┐
                                 │                 │
                           ┌────►│ Social          │
                           │     │ Aggregator      │
                           │     │                 │
                           │     └────────┬────────┘
                           │              │
                           │              │ Social Data
┌─────────────┐   Requests │              ▼
│             │            │     ┌─────────────────┐
│ User        ├────────────┼────►│                 │      ┌─────────────────┐
│ Interface   │            │     │ Correlation     │◄─────┤                 │
│ (Web/API)   │◄───────────┼─────┤ Engine          │      │ On-chain        │
│             │   Reports  │     │                 │◄─────┤ Monitor         │
└─────────────┘            │     └────────┬────────┘      │                 │
                           │              │               └─────────────────┘
                           │              │ Analysis
                           │              ▼
                           │     ┌─────────────────┐
                           │     │                 │
                           └────►│ Pump & Dump     │
                                 │ Analyzer        │
                                 │                 │
                                 └────────┬────────┘
                                          │
                                          │ Alerts
                                          ▼
                                 ┌─────────────────┐
                                 │                 │
                                 │ Alerting        │
                                 │ System          │
                                 │                 │
                                 └─────────────────┘
```

## Core Components

### Pump and Dump Analyzer

The pump and dump analyzer is the core analytical engine that processes token transaction data to identify potential pump-and-dump patterns. It is implemented in `correlation_engine/pump_dump_analyzer.py`.

#### Key Features:

- **Transaction Analysis**: Analyzes buy/sell patterns and volume spikes
- **Wallet Pattern Detection**: Identifies potential "dumper" wallets with suspicious outflow behavior
- **Holder Concentration Analysis**: Examines token distribution across wallets
- **AI-Powered Analysis**: Uses advanced language models to evaluate transaction patterns and generate narratives
- **Confidence Scoring**: Provides a confidence score for each analysis

#### Main Functions:

- `analyze_token_transactions(token_data, extracted_tweets=None)`: Main entry point for analyzing token transaction data
- `analyze_with_ai(token_data, extracted_tweets=None)`: Uses OpenAI models for deeper pattern analysis
- `generate_pump_dump_report(token_address, token_data, analysis_result, token_tweets=None)`: Creates detailed human-readable reports

### Social Media Aggregator

The social media aggregator collects and processes data from Twitter and potentially other social platforms. It looks for mentions of Solana tokens and promotional patterns.

#### Key Features:

- **Keyword Monitoring**: Monitors Twitter for specific keywords related to token promotion
- **Contract Address Extraction**: Identifies and extracts Solana token addresses from tweets
- **Sentiment Analysis**: Analyzes tweet sentiment to identify promotional content
- **Influencer Tracking**: Identifies accounts frequently promoting tokens

### On-chain Monitor

The on-chain monitor interacts with the Solana blockchain via Solscan's API to collect transaction data, token metadata, and holder information.

#### Key Features:

- **Transaction Data Collection**: Fetches detailed transaction history for tokens
- **Token Metadata Retrieval**: Gets token name, symbol, supply, and other metadata
- **Holder Information**: Identifies current token holders and their balances
- **DeFi Activity Tracking**: Monitors interactions with decentralized exchanges

### Correlation Engine

The correlation engine links social media activity with on-chain transactions to identify coordinated pump-and-dump attempts.

#### Key Features:

- **Temporal Correlation**: Maps social promotion to subsequent transaction activity
- **Volume-Mention Correlation**: Identifies relationships between social mentions and trading volume
- **Promoter-Dumper Correlation**: Attempts to link promoters to wallets that dump tokens

### Alerting System

The alerting system notifies users of potential pump-and-dump schemes once they've been detected.

#### Key Features:

- **Email Alerts**: Sends email notifications with analysis results
- **Configurable Thresholds**: Allows users to set sensitivity levels for alerts
- **Report Generation**: Creates detailed PDF/text reports for review

## API Reference

The system provides a REST API for programmatic access, implemented in `api.py`.

### Endpoints:

#### POST /api/analyze

Analyzes a specific token for pump-and-dump characteristics.

**Request:**
```json
{
  "token_address": "TOKENADDRESSHERE"
}
```

**Response:**
```json
{
  "report_content": "Full report text...",
  "is_pump_dump": true,
  "confidence": 0.85
}
```

## Configuration Guide

The system is highly configurable through the `config/settings.py` file and environment variables.

### Essential Configuration:

1. **API Keys**:
   - `TWITTER_API_KEY`: API key for Twitter access
   - `SOLSCAN_API_KEY`: API key for Solscan Pro API access
   - `OPENAI_API_KEY`: API key for OpenAI (optional, enhances analysis)

2. **Social Media Monitoring**:
   - `TWITTER_KEYWORDS`: List of keywords to monitor on Twitter
   - `TWITTER_USER_AGENTS`: User agents to use when scraping Twitter

3. **Analysis Parameters**:
   - `CORRELATION_TIME_WINDOW_MINUTES`: Time window for correlating social and on-chain activity
   - `SENTIMENT_SPIKE_THRESHOLD`: Threshold for identifying suspicious sentiment spikes
   - `VOLUME_SPIKE_THRESHOLD_PERCENT`: Threshold for identifying suspicious volume spikes

4. **General Settings**:
   - `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, WARNING, ERROR)
   - `CHECK_INTERVAL_SECONDS`: Interval between monitoring cycles

### Environment Variables

Create a `.env` file in the project root directory based on the provided `env_example.txt` template.

## Implementation Details

### Pump and Dump Detection Algorithm

The detection algorithm uses a multi-factor approach:

1. **Initial Filtering**:
   - Checks for minimum transaction count (e.g., > 10 transactions)
   - Verifies token has metadata and holder information

2. **Volume Analysis**:
   - Converts transactions to hourly time series
   - Identifies volume spikes (e.g., 3x average of previous hours)
   - Calculates buy/sell ratio (suspicious if sells > 70% of transactions)

3. **Wallet Pattern Analysis**:
   - Identifies potential dumpers (wallets with high outflow ratio)
   - Identifies whale wallets (holding significant % of supply)
   - Measures wallet concentration (suspicious if top 3 wallets hold >50%)

4. **Confidence Calculation**:
   - Assigns weights to different factors:
     - High sell ratio: +0.2 confidence
     - Volume spikes: +0.1-0.3 confidence based on magnitude
     - Presence of dumpers: +0.1-0.2 confidence
     - High wallet concentration: +0.2 confidence

5. **AI Enhancement**:
   - When API key is available, sends data to AI for deeper analysis
   - AI model analyzes all factors plus qualitative aspects of transactions
   - AI can override heuristic confidence score if it finds stronger evidence

### OpenAI Integration

The system integrates with OpenAI's language models to enhance analysis. The AI model:

1. Receives a comprehensive data package including:
   - Token metadata (name, symbol, supply)
   - Holder information
   - Transaction overview
   - Raw transaction samples
   - DeFi activity information
   - Related tweets/social content

2. Returns structured analysis including:
   - Binary determination (is_pump_dump: true/false)
   - Confidence score (0.0-1.0)
   - Detailed narrative explaining patterns found
   - List of potential dumper wallets
   - Summary conclusion

## Deployment Guide

### Prerequisites

- Python 3.8 or higher
- Access to Twitter and Solscan APIs
- OpenAI API key (optional but recommended)

### Deployment Steps

1. **Local Deployment**:
   - Clone the repository
   - Create and activate a virtual environment
   - Install dependencies: `pip install -r requirements.txt`
   - Create `.env` file with required API keys
   - Run the application: `python main.py`

2. **Server Deployment**:
   - Set up a Linux server (Ubuntu/Debian recommended)
   - Clone the repository to `/opt/solana-pump-dump-detector`
   - Create a Python virtual environment: `python -m venv /opt/solana-pump-dump-detector/venv`
   - Install dependencies: `/opt/solana-pump-dump-detector/venv/bin/pip install -r requirements.txt`
   - Create a systemd service to run the application as a background service
   - Set up proper logging to `/var/log/solana-pump-dump-detector.log`
   - Configure firewall to allow access to the API port if needed
   - Consider using a reverse proxy (Nginx/Apache) if exposing the API to the internet

3. **Docker Deployment**:
   - Use the provided Dockerfile in the project root
   - Build the image: `docker build -t solana-pump-dump-detector .`
   - Run the container: `docker run -d -p 5001:5001 -v ./data:/app/data --env-file .env solana-pump-dump-detector`

## Troubleshooting

### Common Issues

#### API Connection Problems

**Symptoms**: Errors in logs about failing to connect to Twitter or Solscan APIs.

**Solutions**:
- Verify API keys are correctly configured in the `.env` file
- Check network connectivity from your server to the API endpoints
- Verify you're not hitting API rate limits
- Test API keys directly using a simple curl request

#### Missing Transaction Data

**Symptoms**: Analysis reports show limited or no transaction data.

**Solutions**:
- Verify the token address is correct and active on Solana
- Ensure the Solscan API key has sufficient permissions
- Check if the token has enough transactions to analyze (minimum 10)
- Try increasing log level to DEBUG to see detailed API responses

#### High CPU/Memory Usage

**Symptoms**: System becomes slow or unresponsive during analysis.

**Solutions**:
- Consider increasing the server specifications
- Adjust batch sizes for processing in `config/settings.py`
- Implement timeouts for external API calls
- Reduce the frequency of monitoring cycles

### Logs and Debugging

The system logs detailed information to help diagnose issues:

- **Log Location**: By default, logs are stored in the project directory
- **Log Levels**: Configure the verbosity in `.env` file (INFO, DEBUG, WARNING, ERROR)
- **Specific Component Logs**:
  - `main_results.log`: Main application logs
  - `twitter_results.log`: Twitter monitoring logs

To enable more detailed debugging:

1. Set `LOG_LEVEL=DEBUG` in your `.env` file
2. Restart the application
3. Check logs for detailed information about API calls, processing steps, and errors

## Performance Optimization

### Handling Large Datasets

For tokens with thousands of transactions, consider the following optimizations:

1. **Sampling**: Configure the system to analyze a representative sample of transactions
2. **Batch Processing**: Process data in smaller batches to reduce memory usage
3. **Time Windowing**: Focus analysis on specific time windows around social media activity
4. **Database Storage**: For production deployments, consider storing analysis results in a database

### API Rate Limiting

To avoid hitting API rate limits:

1. **Caching**: Implement caching for frequently accessed data
2. **Throttling**: Add delays between API calls
3. **Bulk Requests**: Use bulk endpoint requests where available
4. **Upgrade API Tiers**: Consider upgrading to higher API tiers for increased rate limits

## Security Considerations

### API Key Protection

- Store API keys securely in environment variables or a secure key management system
- Never commit API keys to version control
- Consider using credential rotation for production deployments

### Input Validation

The system implements validation for all user inputs to prevent:
- SQL injection attacks
- Command injection
- Parameter tampering

### Network Security

When deploying the API publicly:
- Use HTTPS with a valid SSL certificate
- Implement API authentication
- Consider rate limiting to prevent abuse
- Deploy behind a WAF (Web Application Firewall)

## Future Development

Planned enhancements for future versions:

1. **Additional Data Sources**:
   - Integration with Discord and Telegram for monitoring promotions
   - Supporting more blockchain explorers beyond Solscan

2. **Enhanced Analysis**:
   - Machine learning models trained on historical pump-and-dump schemes
   - Network analysis to identify coordinated wallet clusters
   - Integration with price data sources

3. **UI Improvements**:
   - Interactive dashboards with visualization tools
   - Real-time monitoring interface

4. **Scalability**:
   - Distributed architecture for handling multiple tokens simultaneously
   - Cloud-native deployment options (AWS, GCP, Azure)

## Contributors

This project is maintained by a team of blockchain security researchers and developers. Contributions are welcome via pull requests.

## License

This project is licensed under the BSD 3-Clause License. See the LICENSE file for details. 