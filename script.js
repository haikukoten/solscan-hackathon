/* script.js */
document.addEventListener('DOMContentLoaded', () => {
    // Remove reportSelect as it's no longer used
    // const reportSelect = document.getElementById('report-select'); 
    const reportContent = document.getElementById('report-content');
    const tokenAddressInput = document.getElementById('token-address-input');
    const analyzeButton = document.getElementById('analyze-button');
    const historyList = document.getElementById('history-list');
    
    const historyStorageKey = 'analysisHistory';
    const maxHistoryItems = 15; // Limit the number of items in history

    // --- Load and Display History --- 
    function loadHistory() {
        const history = getHistory();
        historyList.innerHTML = ''; // Clear current list (including placeholder)
        
        if (history.length === 0) {
            const placeholder = document.createElement('li');
            placeholder.className = 'placeholder';
            placeholder.textContent = 'No analysis history yet...';
            historyList.appendChild(placeholder);
            return;
        }
        
        history.forEach(item => {
            const li = document.createElement('li');
            li.textContent = `${item.address.substring(0, 15)}... (${new Date(item.timestamp).toLocaleTimeString()})`;
            li.title = item.address; // Show full address on hover
            li.dataset.address = item.address; // Store address for click event
            li.addEventListener('click', () => {
                tokenAddressInput.value = item.address; // Pre-fill input
                analyzeToken(item.address); // Re-analyze this token
            });
            historyList.appendChild(li);
        });
    }

    function getHistory() {
        const storedHistory = localStorage.getItem(historyStorageKey);
        return storedHistory ? JSON.parse(storedHistory) : [];
    }

    function addToHistory(address) {
        const now = Date.now();
        let history = getHistory();

        // Remove existing entry for the same address to move it to the top
        history = history.filter(item => item.address !== address);

        // Add new entry at the beginning
        history.unshift({ address, timestamp: now });

        // Limit history size
        if (history.length > maxHistoryItems) {
            history = history.slice(0, maxHistoryItems);
        }

        localStorage.setItem(historyStorageKey, JSON.stringify(history));
        loadHistory(); // Refresh the displayed list
    }
    // --- End History Functions ---

    // Removed populateReportList() function as dropdown is gone

    // Removed loadReport() function, analysis is now triggered by analyzeToken

    // --- Analyze Token Function (Modified) ---
    async function analyzeToken(addressToAnalyze = null) {
        // Use provided address (from history click) or input field value
        const tokenAddress = addressToAnalyze || tokenAddressInput.value.trim();
        
        if (!tokenAddress) {
            reportContent.textContent = 'ERROR: Please enter a token address. //_';
            return;
        }

        // Add a typing/processing indicator
        reportContent.textContent = `// PROCESSING REQUEST FOR ${tokenAddress}... STANDBY //`;
        analyzeButton.disabled = true; 
        tokenAddressInput.disabled = true; // Disable input during analysis

        // Add a class to start animation (optional)
        reportContent.classList.add('processing'); 

        try {
            const apiUrl = 'http://localhost:5001/api/analyze'; 
            console.log(`Sending request to ${apiUrl} for token ${tokenAddress}`);

            const response = await fetch(apiUrl, { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token_address: tokenAddress })
            });

            // Remove processing class
            reportContent.classList.remove('processing');

            if (!response.ok) {
                let errorMsg = `Backend error: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorMsg;
                } catch (jsonError) { errorMsg = `${errorMsg} - ${response.statusText}`; }
                throw new Error(errorMsg);
            }

            const result = await response.json();
            const newReportContent = result.report_content;
            
            console.log(`Analysis successful for ${tokenAddress}. Displaying report content.`);
            reportContent.textContent = newReportContent; // Display the report content directly

            // Add to history AFTER successful analysis
            addToHistory(tokenAddress);
            
            if (!addressToAnalyze) { // Clear input only if it wasn't a history click
                tokenAddressInput.value = '';
            } 

        } catch (error) {
            console.error('Analysis request failed:', error);
            reportContent.classList.remove('processing'); // Ensure class is removed on error
            reportContent.textContent = `// ANALYSIS FAILED //\nError: ${error.message}\n\nPlease check the token address and ensure the backend API server is running.`;
        } finally {
            analyzeButton.disabled = false; // Re-enable button
            tokenAddressInput.disabled = false; // Re-enable input
        }
    }
    // --- End Analyze Token Function ---

    // Event listener for Analyze button
    analyzeButton.addEventListener('click', () => analyzeToken()); // Call without argument to use input field

    // Allow pressing Enter in the input field to trigger analysis
    tokenAddressInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            analyzeToken(); // Call without argument to use input field
        }
    });

    // --- Initial Setup ---
    loadHistory(); // Load history on page load
    reportContent.textContent = 'AWAITING INPUT // ENTER TOKEN ADDRESS FOR ANALYSIS //_'; // Set initial text

}); 