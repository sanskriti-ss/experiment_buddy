/**
 * Background Service Worker
 * Handles communication between content scripts and backend API
 */

// Configuration
const API_BASE_URL = 'http://localhost:8000'; // Change to your backend URL
const API_TIMEOUT = 30000; // 30 seconds

/**
 * Handle messages from content scripts
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[BG] Message from content script:', request.action);

  if (request.action === 'analyze-procedure-from-document') {
    analyzeProcedureFromDocument(request.payload)
      .then(result => {
        console.log('[BG] Sending successful result to content script:', result);
        sendResponse({ success: true, result });
      })
      .catch(error => {
        console.error('[BG] Error:', error);
        const errorResponse = {
          success: false,
          error: error.message || 'Analysis failed',
        };
        console.log('[BG] Sending error response to content script:', errorResponse);
        sendResponse(errorResponse);
      });

    // Return true to indicate we'll send response asynchronously
    return true;
  }
});

/**
 * Analyze procedure text from document
 */
async function analyzeProcedureFromDocument(payload) {
  const { text, source, metadata, contentAnalysis } = payload;

  console.log('[BG] Analyzing procedure:', {
    source,
    wordCount: contentAnalysis.wordCount,
    platform: metadata.platform,
  });

  // Check if text contains experimental content
  if (!contentAnalysis.isLikelyProcedure && contentAnalysis.wordCount < 100) {
    console.warn('[BG] Text may not be experimental content');
  }

  // Prepare request payload
  const requestPayload = {
    text,
    source,
    metadata: {
      title: metadata.title,
      url: metadata.url,
      platform: metadata.platform,
      documentId: metadata.documentId,
    },
    contentAnalysis,
  };

  try {
    // Send to backend API
    const response = await fetch(`${API_BASE_URL}/extract`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestPayload),
      timeout: API_TIMEOUT,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();
    console.log('[BG] Analysis complete', result);

    // Handle review article detection
    if (!result.success && result.error === 'review_article_detected') {
      // Pass through the review article response for special handling
      return {
        success: false,
        error: result.error,
        message: result.message,
        suggestion: result.suggestion,
        review_check: result.review_check,
        metadata: result.metadata
      };
    }

    // Handle other errors
    if (!result.success) {
      throw new Error(result.error || 'Analysis failed');
    }

    // Map the successful response to the format expected by content script
    return {
      extracted_procedure: result.procedure_ir || null,
      analysis: result.analysis || null,
      validation_errors: result.validation_errors || [],
      replicability_gaps: result.replicability_gaps || [],
      metadata: result.metadata || {},
    };
  } catch (error) {
    console.error('[BG] API call failed:', error);

    // If backend is unavailable, provide helpful error
    if (error.message.includes('Failed to fetch')) {
      throw new Error(
        'Backend API unavailable. Make sure the Python server is running at ' + API_BASE_URL
      );
    }

    // Re-throw with more context
    throw new Error(`Analysis failed: ${error.message}`);
  }
}

/**
 * Check if the backend is available
 */
async function checkBackendAvailability() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      timeout: 5000,
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Initialize background script
 */
chrome.runtime.onInstalled.addListener(() => {
  console.log('[BG] Extension installed/updated');

  // Check backend availability
  checkBackendAvailability().then(available => {
    if (!available) {
      console.warn('[BG] Backend API not available');
      // Could notify user or set default mode
    }
  });

  // Set default storage values (clear old settings)
  chrome.storage.sync.clear(() => {
    chrome.storage.sync.set({
      apiBaseUrl: 'http://localhost:8888',
      analysisModel: 'openai/gpt-4o-mini',
      autoDetectProcedure: true,
      enableNotifications: true,
    });
    console.log('[BG] Reset extension settings to port 8888');
  });
});

/**
 * Update API base URL from settings
 */
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'sync' && changes.apiBaseUrl) {
    const newUrl = changes.apiBaseUrl.newValue;
    if (newUrl) {
      // Update the global API_BASE_URL
      console.log('[BG] API URL updated to:', newUrl);
    }
  }
});

console.log('[BG] Background service worker loaded');
