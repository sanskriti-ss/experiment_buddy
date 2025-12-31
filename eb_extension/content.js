/**
 * Universal Content Script
 * Loads on any note-taking platform and enables analysis
 * 
 * Flows:
 * 1. Detect platform
 * 2. Load appropriate adapter
 * 3. Inject UI
 * 4. Handle user interactions
 * 5. Send content to background for processing
 */

// Global state
const STATE = {
  adapter: null,
  extractor: null,
  isExtensionReady: false,
  lastAnalysisResult: null,
  uiElement: null,
};

/**
 * Check if extension context is still valid
 */
function isExtensionContextValid() {
  try {
    return chrome.runtime && chrome.runtime.id;
  } catch (error) {
    return false;
  }
}

/**
 * Safely send message with context validation
 */
function safeSendMessage(message, callback) {
  if (!isExtensionContextValid()) {
    console.warn('[Experiment Buddy] Extension context invalidated');
    showNotification('Extension was reloaded. Please refresh the page to continue.', 'warning');
    return;
  }
  
  try {
    chrome.runtime.sendMessage(message, callback);
  } catch (error) {
    console.error('[Experiment Buddy] Error sending message:', error);
    showNotification('Extension communication error. Please refresh the page.', 'error');
  }
}

/**
 * Initialize the extension on the page
 */
function initializeExtension() {
  console.log('[Experiment Buddy] Initializing on page...', window.location.href);

  try {
    // Check if extension context is valid
    if (!isExtensionContextValid()) {
      console.warn('[Experiment Buddy] Extension context invalid at initialization');
      return;
    }

    // Check if dependencies are loaded
    if (typeof PlatformDetector === 'undefined') {
      console.warn('[Experiment Buddy] PlatformDetector not loaded, using fallback');
    }
    if (typeof ContentExtractor === 'undefined') {
      console.warn('[Experiment Buddy] ContentExtractor not loaded, using fallback');
    }

    // Always inject the UI, even if platform detection fails
    // This ensures the extension works on scientific papers too
    
    // Try platform detection
    let adapter, extractor;
    try {
      if (typeof PlatformDetector !== 'undefined') {
        adapter = PlatformDetector.getAdapter();
        extractor = new ContentExtractor(adapter);
        console.log(`[Experiment Buddy] Detected platform: ${adapter.platformName}`);
      } else {
        throw new Error('PlatformDetector not available');
      }
    } catch (error) {
      console.warn('[Experiment Buddy] Platform detection failed, using fallback:', error);
      // Use a basic fallback adapter
      adapter = {
        platformName: 'generic',
        getTextContent: () => {
          // Try multiple methods to get text content
          let text = '';
          
          console.log('[Experiment Buddy] Attempting generic text extraction...');
          
          // Method 1: Try scientific article selectors first
          const scienceSelectors = [
            'article',                    // Generic article tag
            '.c-article-body',           // Common science journal class
            '.article-body',
            '.content-body',
            '#article-content',
            '[data-track="article-body"]',
            '.main-content',
            '[role="article"]'
          ];
          
          for (const selector of scienceSelectors) {
            const element = document.querySelector(selector);
            if (element && element.innerText && element.innerText.trim().length > 200) {
              text = element.innerText;
              console.log(`[Experiment Buddy] Found text via selector: ${selector}, length: ${text.length}`);
              break;
            }
          }
          
          // Method 2: Try main content areas
          if (!text) {
            const mainSelectors = ['main', '[role="main"]', '.content', '#content'];
            for (const selector of mainSelectors) {
              const element = document.querySelector(selector);
              if (element && element.innerText && element.innerText.trim().length > 200) {
                text = element.innerText;
                console.log(`[Experiment Buddy] Found text via main selector: ${selector}, length: ${text.length}`);
                break;
              }
            }
          }
          
          // Method 3: If no main content, try paragraphs
          if (!text) {
            const paragraphs = document.querySelectorAll('p');
            if (paragraphs.length > 0) {
              text = Array.from(paragraphs).map(p => p.innerText).filter(t => t.trim().length > 0).join('\n');
              console.log(`[Experiment Buddy] Found text via paragraphs: ${paragraphs.length} paragraphs, total length: ${text.length}`);
            }
          }
          
          // Method 4: Last resort - get body text  
          if (!text || text.trim().length < 100) {
            text = document.body.innerText || document.body.textContent || '';
            console.log(`[Experiment Buddy] Using body text as fallback, length: ${text.length}`);
          }
          
          console.log(`[Experiment Buddy] Final text preview:`, text.substring(0, 300));
          return text.trim();
        },
        getSelectedText: () => window.getSelection().toString(),
        insertUI: (element) => {
          element.style.position = 'fixed';
          element.style.bottom = '20px';
          element.style.right = '20px';
          element.style.zIndex = '999999';
          document.body.appendChild(element);
        },
        getMetadata: () => ({ 
          title: document.title, 
          url: window.location.href,
          platform: 'generic'
        }),
        isApplicable: () => true
      };
      
      // Create a fallback extractor if the class isn't available
      if (typeof ContentExtractor !== 'undefined') {
        extractor = new ContentExtractor(adapter);
        console.log('[Experiment Buddy] Using ContentExtractor class');
      } else {
        console.warn('[Experiment Buddy] ContentExtractor class not available, using basic extractor');
        extractor = {
          extractSelectedText: () => {
            const selected = window.getSelection().toString();
            console.log('[Experiment Buddy] Basic extractor - selected text length:', selected.length);
            return selected;
          },
          extractFullText: () => {
            console.log('[Experiment Buddy] Basic extractor - calling adapter.getTextContent()');
            const result = adapter.getTextContent();
            console.log('[Experiment Buddy] Basic extractor - adapter.getTextContent() returned length:', result ? result.length : 'null/undefined');
            return result;
          },
          extractRelevantText: () => {
            console.log('[Experiment Buddy] Basic extractor - calling adapter.getTextContent() for relevant text');
            return adapter.getTextContent();
          },
          getDocumentMetadata: () => adapter.getMetadata()
        };
        console.log('[Experiment Buddy] Created basic extractor:', extractor);
      }
    }

    STATE.adapter = adapter;
    STATE.extractor = extractor;

    // Always inject UI for testing
    injectUI();

    // Mark as ready
    STATE.isExtensionReady = true;

    // Start periodic health check
    startHealthCheck();

    console.log('[Experiment Buddy] Ready on', adapter.platformName);
  } catch (error) {
    console.error('[Experiment Buddy] Initialization failed:', error);
  }
}

/**
 * Start periodic health check to monitor extension context
 */
function startHealthCheck() {
  setInterval(() => {
    if (!isExtensionContextValid() && STATE.isExtensionReady) {
      console.warn('[Experiment Buddy] Extension context lost, disabling UI');
      STATE.isExtensionReady = false;
      
      // Update UI to show context lost
      const button = document.getElementById('experiment-buddy-button');
      if (button) {
        button.style.background = 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)';
        button.title = 'Extension context lost - Please refresh page';
        button.innerHTML = '⚠️';
      }
    }
  }, 5000); // Check every 5 seconds
}

/**
 * Inject the Experiment Buddy UI into the page
 */
function injectUI() {
  // Create container
  const container = document.createElement('div');
  container.id = 'experiment-buddy-container';
  container.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 999999;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  // Create button
  const button = document.createElement('button');
  button.id = 'experiment-buddy-button';
  button.innerHTML = 'EB';
  button.title = 'Analyze Experiment Procedure';
  button.style.cssText = `
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    border: none;
    color: white;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    transition: all 0.3s ease;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  `;

  button.addEventListener('mouseenter', () => {
    button.style.transform = 'scale(1.1)';
    button.style.boxShadow = '0 6px 16px rgba(37, 99, 235, 0.6)';
  });

  button.addEventListener('mouseleave', () => {
    button.style.transform = 'scale(1)';
    button.style.boxShadow = '0 4px 12px rgba(37, 99, 235, 0.4)';
  });

  button.addEventListener('click', () => {
    // Check extension context before handling click
    if (!isExtensionContextValid()) {
      showNotification('Extension was reloaded. Please refresh the page to continue.', 'warning');
      return;
    }
    handleAnalyzeClick();
  });

  // Create menu
  const menu = document.createElement('div');
  menu.id = 'experiment-buddy-menu';
  menu.style.display = 'none';
  menu.style.cssText += `
    position: absolute;
    bottom: 70px;
    right: 0;
    background: white;
    border-radius: 8px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.16);
    overflow: hidden;
    min-width: 200px;
  `;

  const menuItems = [
    { label: 'Analyze Selected Text', action: 'analyze-selected' },
    { label: 'Analyze Full Document', action: 'analyze-full' },
    { label: 'Analyze Methods Section', action: 'analyze-smart' },
    { label: 'Debug Page Structure', action: 'debug-page' },
    { label: 'Settings', action: 'settings' },
  ];

  menuItems.forEach((item, index) => {
    const menuItem = document.createElement('button');
    menuItem.innerHTML = item.label;
    menuItem.style.cssText = `
      display: block;
      width: 100%;
      padding: 12px 16px;
      border: none;
      background: ${index === 0 ? '#f5f5f5' : 'white'};
      cursor: pointer;
      text-align: left;
      font-size: 13px;
      color: #333;
      border-bottom: ${index < menuItems.length - 1 ? '1px solid #eee' : 'none'};
      transition: background 0.2s;
    `;

    menuItem.addEventListener('mouseenter', () => {
      menuItem.style.background = '#f5f5f5';
    });

    menuItem.addEventListener('mouseleave', () => {
      menuItem.style.background = index === 0 ? '#f5f5f5' : 'white';
    });

    menuItem.addEventListener('click', () => {
      handleMenuItemClick(item.action);
      toggleMenu();
    });

    menu.appendChild(menuItem);
  });

  container.appendChild(button);
  container.appendChild(menu);

  STATE.adapter.insertUI(container);
  STATE.uiElement = container;
}

/**
 * Toggle the menu visibility
 */
function toggleMenu() {
  const menu = document.getElementById('experiment-buddy-menu');
  if (menu) {
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
  }
}

/**
 * Handle main button click - toggle menu
 */
function handleAnalyzeClick() {
  toggleMenu();
}

/**
 * Handle menu item selection
 */
function handleMenuItemClick(action) {
  let text = '';
  let source = '';

  switch (action) {
    case 'analyze-selected': {
      const selected = STATE.extractor.extractSelectedText();
      if (!selected) {
        showNotification('Please select some text first', 'warning');
        return;
      }
      text = selected;
      source = 'lab_notes';  // Map to valid schema value
      break;
    }
    case 'analyze-full': {
      console.log('[Experiment Buddy] Starting full text extraction...');
      console.log('[Experiment Buddy] STATE.extractor:', STATE.extractor);
      console.log('[Experiment Buddy] STATE.adapter:', STATE.adapter);
      
      text = STATE.extractor.extractFullText();
      console.log('[Experiment Buddy] Full text extracted, length:', text ? text.length : 'null/undefined');
      if (text && text.length > 100) {
        console.log('[Experiment Buddy] Full text preview:', text.substring(0, 200) + '...');
      } else {
        console.warn('[Experiment Buddy] Full text extraction returned insufficient content:', text);
      }
      source = 'other';  // Map to valid schema value
      break;
    }
    case 'analyze-smart': {
      text = STATE.extractor.extractRelevantText();
      source = 'methods_section';  // Map to valid schema value
      break;
    }
    case 'debug-page': {
      debugPageStructure();
      return;
    }
    case 'settings': {
      openSettings();
      return;
    }
    default:
      return;
  }

  if (!text || text.trim().length === 0) {
    console.warn('[Experiment Buddy] No text extracted. Adapter:', STATE.adapter.platformName);
    showNotification('No text content found. Try selecting text first.', 'warning');
    return;
  }

  // Analyze the text content
  analyzeText(text, source);
}

/**
 * Send text for analysis to the backend
 */
function analyzeText(text, source) {
  let cleanedText, analysis, metadata;
  
  try {
    // Use ContentExtractor methods if available, otherwise use fallbacks
    if (typeof ContentExtractor !== 'undefined' && ContentExtractor.cleanText) {
      cleanedText = ContentExtractor.cleanText(text);
      analysis = ContentExtractor.analyzeTextContent(text);
    } else {
      // Fallback text cleaning
      cleanedText = text.replace(/\s+/g, ' ').trim();
      analysis = {
        wordCount: cleanedText.split(' ').length,
        keywords: [],
        hasExperimentalContent: cleanedText.toLowerCase().includes('method'),
        isLikelyProcedure: true
      };
    }
    
    metadata = STATE.extractor.getDocumentMetadata();
  } catch (error) {
    console.error('[Experiment Buddy] Error in text analysis setup:', error);
    // Fallback values
    cleanedText = text.replace(/\s+/g, ' ').trim();
    analysis = { wordCount: cleanedText.split(' ').length, keywords: [] };
    metadata = { title: document.title, url: window.location.href, platform: 'generic' };
  }

  console.log('[Experiment Buddy] Analyzing text...', {
    source,
    wordCount: analysis.wordCount,
    keywords: analysis.keywords,
  });

  // Show loading state
  showNotification('Analyzing procedure...', 'info');

  // Send to background script for processing with safe message handling
  safeSendMessage(
    {
      action: 'analyze-procedure-from-document',
      payload: {
        text: cleanedText,
        source,
        metadata,
        contentAnalysis: analysis,
      },
    },
    (response) => {
      // Check for extension context invalidation
      if (chrome.runtime.lastError) {
        console.error('[Experiment Buddy] Runtime error:', chrome.runtime.lastError);
        
        if (chrome.runtime.lastError.message.includes('Extension context invalidated')) {
          showNotification('Extension was reloaded. Please refresh the page to continue.', 'warning');
          return;
        }
        
        showNotification('Error: ' + chrome.runtime.lastError.message, 'error');
        return;
      }

      if (response && response.success) {
        STATE.lastAnalysisResult = response.result;
        showAnalysisResult(response.result);
      } else {
        // Handle review article detection - can come from result or directly from response
        const reviewInfo = response?.result || response;
        if (reviewInfo && reviewInfo.error === 'review_article_detected') {
          showReviewArticleNotification(reviewInfo);
        } else {
          showNotification(
            response?.result?.error || response?.error || 'Analysis failed',
            'error'
          );
        }
      }
    }
  );
}

/**
 * Show a specialized notification for review articles
 */
function showReviewArticleNotification(response) {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: #fef3cd;
    border: 1px solid #facc15;
    color: #713f12;
    padding: 16px 20px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    max-width: 400px;
    z-index: 9999999;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.5;
  `;

  const reviewData = response.review_check || {};
  
  notification.innerHTML = `
    <div style="display: flex; align-items: flex-start;">
      <div style="margin-right: 12px; font-size: 20px;">⚠️</div>
      <div>
        <div style="font-weight: 600; margin-bottom: 8px;">Review Article Detected</div>
        <div style="margin-bottom: 8px;">${response.message || 'This appears to be a review article rather than original research with methods.'}</div>
        <div style="margin-bottom: 12px; font-style: italic;">${response.suggestion || 'Please select a Methods section from an original research paper.'}</div>
        ${reviewData.confidence ? `<div style="font-size: 12px; color: #92400e;">Confidence: ${Math.round(reviewData.confidence * 100)}%</div>` : ''}
      </div>
      <button onclick="this.parentElement.parentElement.remove()" style="
        background: none;
        border: none;
        font-size: 16px;
        cursor: pointer;
        color: #92400e;
        padding: 0;
        margin-left: auto;
      ">×</button>
    </div>
  `;

  document.body.appendChild(notification);

  // Auto-remove after 10 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 10000);
}

/**
 * Format missing parameters into human-friendly descriptions
 */
function formatMissingParameters(missingParams) {
  const paramMap = {
    'duration': 'how long to perform this step',
    'temperature': 'temperature setting',
    'concentration': 'concentration amount',
    'volume': 'volume measurement',
    'reagent': 'specific reagent or chemical name',
    'antibody': 'antibody name and concentration',
    'time': 'timing information',
    'speed': 'centrifuge or mixing speed',
    'buffer': 'buffer solution details',
    'medium': 'culture medium type',
    'cell_line': 'specific cell line used',
    'passage_number': 'cell passage number',
    'seeding_density': 'cell seeding density',
    'incubation_time': 'incubation duration',
    'incubation_temperature': 'incubation temperature',
    'wash_buffer': 'washing buffer type',
    'wash_steps': 'number of wash steps',
    'centrifuge_speed': 'centrifugation speed',
    'centrifuge_time': 'centrifugation duration',
    'dilution': 'dilution ratio',
    'ph': 'pH level',
    'osmolarity': 'osmolarity value',
    'fixation_time': 'fixation duration',
    'permeabilization': 'permeabilization method',
    'blocking_solution': 'blocking solution details',
    'primary_antibody': 'primary antibody information',
    'secondary_antibody': 'secondary antibody details',
    'microscope_settings': 'microscopy parameters',
    'magnification': 'magnification level',
    'exposure_time': 'camera exposure time',
    'wavelength': 'light wavelength or filter',
    'objective': 'microscope objective lens'
  };

  return missingParams.map(param => 
    paramMap[param] || param.replace(/_/g, ' ')
  ).join(', ');
}

/**
 * Display analysis results in a modal/panel
 */
function showAnalysisResult(result) {
  console.log('[Experiment Buddy] Showing analysis result:', result);
  
  if (!result) {
    showNotification('No analysis result received', 'error');
    return;
  }

  // Create a modal
  const modal = document.createElement('div');
  modal.id = 'experiment-buddy-results-modal';
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999999;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  const panel = document.createElement('div');
  panel.style.cssText = `
    background: white;
    border-radius: 12px;
    max-width: 700px;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    padding: 24px;
  `;

  // Build result HTML
  let html = '<h2 style="margin-top: 0; color: #2563eb;">Analysis Results</h2>';

  // Show extracted procedure info
  if (result.extracted_procedure && result.extracted_procedure.steps) {
    const procedure = result.extracted_procedure;
    html += `
      <div style="margin-bottom: 20px;">
        <h3 style="color: #333; margin-bottom: 8px;">Extracted Procedure</h3>
        <p style="color: #666; margin: 0;">
          <strong>Steps:</strong> ${procedure.steps?.length || 0}
        </p>
        ${procedure.citation ? `<p style="color: #666; margin: 4px 0;"><strong>Source:</strong> ${procedure.citation}</p>` : ''}
      </div>
    `;
  } else if (result.extracted_procedure) {
    html += `
      <div style="margin-bottom: 20px; padding: 12px; background: #f8f9fa; border-radius: 6px;">
        <p style="color: #666; margin: 0;">
          ⚠️ Procedure was extracted but may not contain clear experimental steps.
        </p>
      </div>
    `;
  } else {
    html += `
      <div style="margin-bottom: 20px; padding: 12px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;">
        <p style="color: #856404; margin: 0;">
          ⚠️ No experimental procedure could be extracted from the text.
        </p>
      </div>
    `;
  }

  if (result.analysis) {
    const analysis = result.analysis;
    html += `
      <div style="margin-bottom: 20px;">
        <h3 style="color: #333; margin-bottom: 8px;">Completeness Analysis</h3>
        <p style="color: #666; margin: 0;">
          <strong>Complete Steps:</strong> ${analysis.complete_steps || 0} / ${analysis.total_steps || 0}
        </p>
        <p style="color: #666; margin: 4px 0;">
          <strong>Overall Score:</strong> ${Math.round((analysis.overall_score || 0) * 100)}%
        </p>
      </div>
    `;

    // Show detailed missing information if available
    if (analysis.steps && analysis.steps.length > 0) {
      const incompleteSteps = analysis.steps.filter(step => !step.is_complete);
      
      if (incompleteSteps.length > 0) {
        html += `
          <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; padding: 12px; margin-bottom: 20px;">
            <h4 style="margin-top: 0; color: #856404;">Missing Details for Reproducibility:</h4>
        `;
        
        incompleteSteps.forEach((step, index) => {
          const stepNumber = analysis.steps.indexOf(step) + 1;
          const actionType = step.action.replace(/_/g, ' ');
          const missingParams = step.missing_parameters || [];
          
          if (missingParams.length > 0) {
            html += `
              <div style="margin-bottom: 12px; padding: 8px; background: rgba(255, 255, 255, 0.7); border-radius: 4px;">
                <p style="margin: 0 0 4px 0; font-weight: bold; color: #856404;">
                  Step ${stepNumber} (${actionType}):
                </p>
                <p style="margin: 0; color: #856404; font-size: 14px;">
                  Missing: ${formatMissingParameters(missingParams)}
                </p>
              </div>
            `;
          }
        });
        
        html += `</div>`;
      } else {
        html += `
          <div style="background: #d4edda; border: 1px solid #c3e6cb; border-radius: 6px; padding: 12px; margin-bottom: 20px;">
            <p style="margin: 0; color: #155724;">
              All procedure steps contain the necessary details for reproducibility!
            </p>
          </div>
        `;
      }
    } else if (analysis.incomplete_steps && analysis.incomplete_steps > 0) {
      html += `
        <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; padding: 12px; margin-bottom: 20px;">
          <p style="margin: 0; color: #856404;">
            Some procedure steps are missing required details for reproducibility.
          </p>
        </div>
      `;
    }
  }

  if (result.validation_errors && result.validation_errors.length > 0) {
    html += `
      <div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 12px; margin-bottom: 20px;">
        <h4 style="margin-top: 0; color: #721c24;">Schema Validation Issues:</h4>
        <ul style="margin: 8px 0; padding-left: 20px; color: #721c24;">
          ${result.validation_errors.map(err => `<li>${err}</li>`).join('')}
        </ul>
      </div>
    `;
  }

  // Add replicability gaps analysis
  if (result.replicability_gaps && result.replicability_gaps.length > 0) {
    html += `
      <div style="background: #e8f4fd; border: 1px solid #2563eb; border-radius: 6px; padding: 12px; margin-bottom: 20px;">
        <h4 style="margin-top: 0; color: #1e40af;">Replicability Analysis:</h4>
        <p style="margin: 0 0 8px 0; color: #1e40af; font-size: 14px;">
          Specific details needed for another researcher to replicate this work:
        </p>
        <ul style="margin: 8px 0; padding-left: 20px; color: #1e40af;">
          ${result.replicability_gaps.map(gap => `<li style="margin-bottom: 6px;">${gap}</li>`).join('')}
        </ul>
      </div>
    `;
  }

  // Add close button
  html += `
    <div style="margin-top: 20px; display: flex; gap: 12px;">
      <button id="close-results" style="
        flex: 1;
        padding: 10px 16px;
        background: #f0f0f0;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
        color: #333;
      ">Close</button>
      <button id="export-results" style="
        flex: 1;
        padding: 10px 16px;
        background: #667eea;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
      ">Export Results</button>
    </div>
  `;

  panel.innerHTML = html;
  modal.appendChild(panel);
  document.body.appendChild(modal);

  // Add event listeners
  document.getElementById('close-results').addEventListener('click', () => {
    modal.remove();
  });

  document.getElementById('export-results').addEventListener('click', () => {
    exportResults(result);
  });

  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

/**
 * Show a notification message
 */
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    bottom: 100px;
    right: 20px;
    background: ${type === 'error' ? '#f8d7da' : type === 'warning' ? '#fff3cd' : '#d1ecf1'};
    border: 1px solid ${type === 'error' ? '#f5c6cb' : type === 'warning' ? '#ffc107' : '#bee5eb'};
    color: ${type === 'error' ? '#721c24' : type === 'warning' ? '#856404' : '#0c5460'};
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 13px;
    z-index: 999998;
    animation: fadeInUp 0.3s ease;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = 'fadeOutDown 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

/**
 * Export analysis results
 */
function exportResults(result) {
  const data = {
    timestamp: new Date().toISOString(),
    platform: STATE.adapter.platformName,
    ...result,
  };

  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `experiment-analysis-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  showNotification('Results exported', 'info');
}

/**
 * Debug page structure to help identify content selectors
 */
function debugPageStructure() {
  console.log('[Experiment Buddy] === PAGE DEBUG INFO ===');
  console.log('URL:', window.location.href);
  console.log('Title:', document.title);
  
  // Check for common content selectors
  const selectors = [
    'article', 'main', '[role="main"]', '[role="article"]',
    '.article-body', '.c-article-body', '.content-body',
    '.main-content', '#content', '#article-content',
    '[data-track="article-body"]', '.article__body',
    'section', '.section', '[class*="article"]', '[class*="content"]'
  ];
  
  console.log('Content elements found:');
  selectors.forEach(selector => {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
      elements.forEach((el, i) => {
        console.log(`  ${selector}[${i}]: ${el.innerText ? el.innerText.substring(0, 100) + '...' : 'no text'}`);
      });
    }
  });
  
  // Check paragraphs
  const paragraphs = document.querySelectorAll('p');
  console.log(`Total paragraphs: ${paragraphs.length}`);
  if (paragraphs.length > 0) {
    console.log('First 3 paragraphs:');
    for (let i = 0; i < Math.min(3, paragraphs.length); i++) {
      console.log(`  p[${i}]: ${paragraphs[i].innerText.substring(0, 100)}...`);
    }
  }
  
  showNotification('Debug info logged to console', 'info');
}

/**
 * Open settings page
 */
function openSettings() {
  const url = chrome.runtime.getURL('settings.html');
  window.open(url, '_blank');
}

/**
 * Handle messages from background script or popup
 */
function handleMessage(request, sender, sendResponse) {
  console.log('[Experiment Buddy] Message received:', request.action);

  switch (request.action) {
    case 'ping':
      sendResponse({ pong: true });
      return false; // Sync response

    case 'analyze-selected-text':
      handleMenuItemClick('analyze-selected');
      sendResponse({ success: true });
      return false; // Sync response

    case 'analyze-full-document':
      handleMenuItemClick('analyze-full');
      sendResponse({ success: true });
      return false; // Sync response

    case 'analyze-methods-section':
      handleMenuItemClick('analyze-smart');
      sendResponse({ success: true });
      return false; // Sync response

    case 'get-selected-text':
      sendResponse({
        text: STATE.extractor.extractSelectedText() || '',
        platform: STATE.adapter.platformName,
      });
      return false; // Sync response

    default:
      sendResponse({ error: 'Unknown action' });
      return false; // Sync response
  }
}

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes fadeOutDown {
    from {
      opacity: 1;
      transform: translateY(0);
    }
    to {
      opacity: 0;
      transform: translateY(20px);
    }
  }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeExtension);
} else {
  // If DOM is already loaded, initialize immediately
  setTimeout(initializeExtension, 100);
}

// Set up message listener immediately (don't wait for initialization)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[Experiment Buddy] Global message received:', request.action);
  
  // Check if extension context is still valid
  if (!isExtensionContextValid()) {
    console.warn('[Experiment Buddy] Extension context invalidated, ignoring message');
    sendResponse({ error: 'Extension context invalidated' });
    return false;
  }
  
  if (request.action === 'ping') {
    sendResponse({ pong: true, initialized: STATE.isExtensionReady });
    return true; // Keep async response channel open
  }
  
  // For other messages, delegate to the handler if initialized
  if (STATE.isExtensionReady && typeof handleMessage === 'function') {
    const result = handleMessage(request, sender, sendResponse);
    return true; // Keep async response channel open
  } else {
    console.warn('[Experiment Buddy] Extension not ready for action:', request.action);
    sendResponse({ error: 'Extension not ready', action: request.action });
    return false;
  }
});

console.log('[Experiment Buddy] Content script loaded on:', window.location.href);
