"""Flask API for triggering Solana token analysis and serving reports."""

import logging
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Configure logging (consider moving to a shared config module)
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Import the core analysis logic ---
# Assuming main.py is structured to allow importing analyze_specific_token
try:
    # If analyze_specific_token can be imported directly:
    from main import analyze_specific_token 
    # If it's better structured in another module, import from there, e.g.:
    # from analysis_engine import analyze_specific_token
except ImportError as e:
    logger.error(f"Could not import analyze_specific_token: {e}")
    logger.error("Ensure main.py or the relevant module is importable and doesn't run full analysis on import.")
    # Fallback: Define a placeholder if import fails
    def analyze_specific_token(token_address: str, scan_twitter: bool = True):
        logger.error("analyze_specific_token could not be imported. Using placeholder.")
        # Simulate report creation
        report_path = f"data/reports/token_{token_address[:10]}_placeholder_report.txt"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(f"Placeholder report for {token_address}. Analysis function not imported.")
        return report_path
# --- End Import ---


# --- Flask App Initialization ---
app = Flask(__name__, static_folder=None) # We'll serve static files manually if needed

# Enable CORS for requests from the frontend (adjust origins if needed)
CORS(app, resources={r"/api/*": {"origins": "*"}}) # Allow all origins for now

# Define the reports directory relative to this script's location
# Ensure this matches where analyze_specific_token saves reports
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'reports'))
os.makedirs(REPORTS_DIR, exist_ok=True) # Ensure the directory exists
logger.info(f"Reports directory set to: {REPORTS_DIR}")
# --- End Initialization ---


# --- API Endpoints ---
@app.route('/api/analyze', methods=['POST'])
def handle_analyze():
    """
    Endpoint to trigger token analysis.
    Expects JSON: { "token_address": "<address>" }
    Returns JSON: { "report_content": "report_content_string" } or { "error": "message" }
    """
    if not request.is_json:
        logger.warning("Received non-JSON request to /api/analyze")
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    token_address = data.get('token_address')

    if not token_address:
        logger.warning("Missing 'token_address' in request body")
        return jsonify({"error": "Missing 'token_address' in request body"}), 400

    logger.info(f"Received analysis request for token: {token_address}")
    
    try:
        # --- Call the analysis function ---
        # It returns a tuple: (analysis_result_dict, report_content_string)
        # Ensure scan_twitter is set to True to get Twitter data
        analysis_result, report_content = analyze_specific_token(token_address, scan_twitter=True) 
        # --- Analysis complete ---

        # CORRECT CHECK: Check if the report_content string exists (is not None)
        if report_content is None: 
             logger.error(f"Analysis function ran but did not return report content for {token_address}")
             # Use a more specific error message if needed
             raise ValueError("Analysis completed but no report content generated.")

        logger.info(f"Analysis successful for {token_address}. Returning report content directly.")
        # Return the report content directly
        return jsonify({"report_content": report_content})

    except ImportError as e:
         logger.exception(f"Import error during analysis for {token_address}: {e}")
         return jsonify({"error": f"Server configuration error: Could not import analysis module."}), 500
    except ValueError as e: # Catch the specific error we might raise
        logger.error(f"Value error during analysis for {token_address}: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception(f"Error during analysis for {token_address}: {e}")
        # Provide a generic error to the client, log the details
        return jsonify({"error": f"Analysis failed for token {token_address}. Check server logs."}), 500

# Optional: Add a simple root endpoint for testing
@app.route('/')
def index():
    return "API Server is running. Use /api/analyze to submit tokens."

# --- End API Endpoints ---


# --- Main Execution ---
if __name__ == '__main__':
    # Use environment variables for host/port if available, otherwise defaults
    host = os.getenv('API_HOST', '0.0.0.0') # Listen on all interfaces
    port = int(os.getenv('API_PORT', 5001)) # Use a different port than the frontend server
    
    # Note: Use a proper WSGI server (like Gunicorn or Waitress) for production
    logger.info(f"Starting Flask API server on {host}:{port}")
    app.run(host=host, port=port, debug=False) # Turn debug=True for development ONLY
# --- End Main Execution --- 