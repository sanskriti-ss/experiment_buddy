/**
 * Popup Script for Experiment Buddy Extension
 * 
 * Handles the extension popup interface and communicates with content scripts
 * and background service worker.
 */

// State management
const state = {
  backendConnected: false,
  currentTab: null,
  platformInfo: null,
};

// DOM elements
const elements = {
  backendStatus: null,
  currentPlatform: null,
  platformStatus: null,
  analyzeSelection: null,
  analyzeFull: null,
  analyzeMethods: null,
  openSettings: null,
  instructions: null,
};

/**
 * Initialize popup when DOM is ready
 */
document.addEventListener('DOMContentLoaded', async () => {
  // Get DOM elements
  elements.backendStatus = document.getElementById('backend-status');
  elements.currentPlatform = document.getElementById('current-platform');
  elements.platformStatus = document.getElementById('platform-status');
  elements.analyzeSelection = document.getElementById('analyze-selection');
  elements.analyzeFull = document.getElementById('analyze-full');
  elements.analyzeMethods = document.getElementById('analyze-methods');
  elements.openSettings = document.getElementById('open-settings');
  elements.instructions = document.getElementById('instructions');

  // Set up event listeners
  setupEventListeners();

  // Initialize popup state
  await initializePopup();
});

/**
 * Set up event listeners for buttons
 */
function setupEventListeners() {
  elements.analyzeSelection.addEventListener('click', () => {
    sendMessageToTab('analyze-selected-text');
    window.close();
  });

  elements.analyzeFull.addEventListener('click', () => {
    sendMessageToTab('analyze-full-document');
    window.close();
  });

  elements.analyzeMethods.addEventListener('click', () => {
    sendMessageToTab('analyze-methods-section');
    window.close();
  });

  elements.openSettings.addEventListener('click', () => {
    chrome.tabs.create({ 
      url: chrome.runtime.getURL('settings.html') 
    });
    window.close();
  });
}

/**
 * Initialize popup state by checking backend and current tab
 */
async function initializePopup() {
  try {
    // Get current active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    state.currentTab = tab;

    // Check backend connection
    await checkBackendStatus();

    // Check current platform and tab status
    await checkCurrentPlatform();

  } catch (error) {
    console.error('Failed to initialize popup:', error);
    showError('Failed to initialize extension');
  }
}

/**
 * Check if backend is available
 */
async function checkBackendStatus() {
  try {
    // Get backend URL from storage
    const settings = await chrome.storage.sync.get({ apiBaseUrl: 'http://localhost:8000' });
    const backendUrl = settings.apiBaseUrl;

    // Test connection with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    
    const response = await fetch(`${backendUrl}/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);

    if (response.ok) {
      state.backendConnected = true;
      updateBackendStatus('Backend connected', 'connected');
    } else {
      throw new Error(`Backend returned ${response.status}`);
    }
  } catch (error) {
    state.backendConnected = false;
    updateBackendStatus('Backend unavailable', 'disconnected');
    console.error('Backend check failed:', error);
  }
}

/**
 * Check current platform and whether extension is active
 */
async function checkCurrentPlatform() {
  if (!state.currentTab) {
    updatePlatformInfo('Unknown', 'No active tab');
    return;
  }

  const url = state.currentTab.url;
  
  // Check if we're on a supported platform
  const platform = detectPlatformFromUrl(url);
  
  // Try to communicate with content script regardless of platform
  try {
    const response = await chrome.tabs.sendMessage(state.currentTab.id, {
      action: 'ping'
    });

    if (response && response.pong) {
      updatePlatformInfo(platform || 'Generic', 'Ready to analyze');
      enableAnalysisButtons();
      hideInstructions();
    } else {
      throw new Error('No response from content script');
    }
  } catch (error) {
    console.error('Content script communication failed:', error);
    
    // For supported platforms, suggest refreshing the page
    if (platform && platform !== 'unknown') {
      updatePlatformInfo(platform, 'Please refresh the page');
      disableAnalysisButtons();
    } else {
      handleConnectionFailure(platform);
    }
  }
}

/**
 * Handle connection failure
 */
function handleConnectionFailure(platform) {
  if (!platform || platform === 'unknown') {
    updatePlatformInfo('Unsupported', 'Extension not active on this page');
    disableAnalysisButtons();
    showInstructions();
  } else {
    updatePlatformInfo(platform, 'Content script failed to load');
    disableAnalysisButtons();
    // Show refresh instruction for supported platforms
    elements.platformStatus.textContent = 'Please reload the extension and refresh this page';
  }
}

/**
 * Detect platform from URL
 */
function detectPlatformFromUrl(url) {
  if (!url) return 'unknown';

  const hostname = new URL(url).hostname;

  if (hostname.includes('docs.google.com')) return 'Google Docs';
  if (hostname.includes('notion.so') || hostname.includes('notion.com')) return 'Notion';
  if (hostname.includes('obsidian.md')) return 'Obsidian';
  if (hostname.includes('roamresearch.com')) return 'Roam Research';
  if (hostname.includes('onenote.com') || hostname.includes('office.com')) return 'OneNote';
  if (hostname.includes('evernote.com')) return 'Evernote';
  if (hostname.includes('atlassian.net') || hostname.includes('confluence')) return 'Confluence';
  if (hostname.includes('ncbi.nlm.nih.gov')) return 'PubMed';
  if (hostname.includes('nature.com')) return 'Nature';
  if (hostname.includes('science.org')) return 'Science';
  if (hostname.includes('arxiv.org')) return 'arXiv';
  if (hostname.includes('biorxiv.org')) return 'bioRxiv';

  return 'unknown';
}

/**
 * Send message to content script in current tab
 */
async function sendMessageToTab(action) {
  if (!state.currentTab) {
    showError('No active tab');
    return;
  }

  try {
    await chrome.tabs.sendMessage(state.currentTab.id, {
      action: action
    });
  } catch (error) {
    console.error('Failed to send message to tab:', error);
    showError('Failed to communicate with page. Try refreshing.');
  }
}

/**
 * Update backend status display
 */
function updateBackendStatus(message, statusClass) {
  elements.backendStatus.textContent = message;
  elements.backendStatus.className = `status ${statusClass}`;
}

/**
 * Update platform information display
 */
function updatePlatformInfo(platform, status) {
  elements.currentPlatform.textContent = platform;
  elements.platformStatus.textContent = status;
}

/**
 * Enable analysis buttons
 */
function enableAnalysisButtons() {
  elements.analyzeSelection.disabled = false;
  elements.analyzeFull.disabled = false;
  elements.analyzeMethods.disabled = false;
}

/**
 * Disable analysis buttons
 */
function disableAnalysisButtons() {
  elements.analyzeSelection.disabled = true;
  elements.analyzeFull.disabled = true;
  elements.analyzeMethods.disabled = true;
}

/**
 * Show instructions
 */
function showInstructions() {
  elements.instructions.classList.remove('hidden');
}

/**
 * Hide instructions
 */
function hideInstructions() {
  elements.instructions.classList.add('hidden');
}

/**
 * Show error message
 */
function showError(message) {
  updateBackendStatus(`${message}`, 'disconnected');
}

console.log('[Popup] Script loaded');