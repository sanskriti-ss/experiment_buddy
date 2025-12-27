/**
 * Platform Detector
 * Identifies the current platform (Google Docs, Notion, etc.)
 * and returns appropriate adapter
 */

class PlatformDetector {
  /**
   * Detect which platform we're on
   * @returns {string} Platform identifier ('google-docs', 'notion', 'obsidian', etc.)
   */
  static detectPlatform() {
    const url = window.location.href;
    const hostname = window.location.hostname;

    // Google Docs
    if (hostname.includes('docs.google.com')) {
      return 'google-docs';
    }

    // Notion
    if (hostname.includes('notion.so') || hostname.includes('notion.com')) {
      return 'notion';
    }

    // Obsidian (web version)
    if (hostname.includes('obsidian.md') || document.body.classList.contains('obsidian')) {
      return 'obsidian';
    }

    // Roam Research
    if (hostname.includes('roamresearch.com')) {
      return 'roam-research';
    }

    // OneNote
    if (hostname.includes('onenote.com') || hostname.includes('office.com')) {
      return 'onenote';
    }

    // Evernote
    if (hostname.includes('evernote.com')) {
      return 'evernote';
    }

    // Confluence
    if (hostname.includes('confluence') || hostname.includes('atlassian.net')) {
      return 'confluence';
    }

    // Scientific Journal Sites
    if (hostname.includes('nature.com') || 
        hostname.includes('science.org') ||
        hostname.includes('cell.com') ||
        hostname.includes('plos.org') ||
        hostname.includes('elsevier.com') ||
        hostname.includes('springer.com') ||
        hostname.includes('wiley.com') ||
        hostname.includes('nih.gov') ||
        hostname.includes('ncbi.nlm.nih.gov') ||
        hostname.includes('biorxiv.org') ||
        hostname.includes('arxiv.org')) {
      return 'scientific-paper';
    }

    // Generic web text editor
    if (this.hasContentEditable()) {
      return 'generic-editor';
    }

    return 'unknown';
  }

  /**
   * Check if the page has contentEditable elements
   */
  static hasContentEditable() {
    return document.querySelectorAll('[contenteditable="true"]').length > 0;
  }

  /**
   * Get the appropriate adapter for the detected platform
   * @returns {Object} Adapter instance
   */
  static getAdapter() {
    const platform = this.detectPlatform();

    const adapters = {
      'google-docs': GoogleDocsAdapter,
      'notion': NotionAdapter,
      'obsidian': ObsidianAdapter,
      'roam-research': RoamResearchAdapter,
      'onenote': OneNoteAdapter,
      'evernote': EvernoteAdapter,
      'confluence': ConfluenceAdapter,
      'generic-editor': GenericEditorAdapter,
      'scientific-paper': ScientificPaperAdapter,
      'unknown': ScientificPaperAdapter,  // Add adapter for unknown platforms
    };

    // Default to ScientificPaperAdapter for better scientific paper support
    const AdapterClass = adapters[platform] || ScientificPaperAdapter;
    return new AdapterClass();
  }
}

/**
 * Base Adapter Class
 * All platform-specific adapters should extend this
 */
class BasePlatformAdapter {
  constructor() {
    this.platformName = 'unknown';
  }

  /**
   * Get all selectable text from the current document/page
   * @returns {string} Combined text content
   */
  getTextContent() {
    throw new Error('getTextContent() must be implemented by subclass');
  }

  /**
   * Get currently selected text
   * @returns {string} Selected text or empty string
   */
  getSelectedText() {
    return window.getSelection().toString();
  }

  /**
   * Insert a UI element into the page for analysis display
   * @param {HTMLElement} element - Element to insert
   */
  insertUI(element) {
    throw new Error('insertUI() must be implemented by subclass');
  }

  /**
   * Get document metadata (title, author, etc.)
   * @returns {Object} Metadata
   */
  getMetadata() {
    return {
      title: document.title,
      url: window.location.href,
      platform: this.platformName,
    };
  }

  /**
   * Check if the adapter is applicable to current page
   * @returns {boolean}
   */
  isApplicable() {
    return true;
  }
}

/**
 * Google Docs Adapter
 */
class GoogleDocsAdapter extends BasePlatformAdapter {
  constructor() {
    super();
    this.platformName = 'google-docs';
  }

  getTextContent() {
    // Google Docs stores content in divs with specific classes
    const contentDivs = document.querySelectorAll('div[data-paragraph-id]');
    const textArray = Array.from(contentDivs).map(div => div.innerText);
    return textArray.join('\n');
  }

  getSelectedText() {
    // Google Docs uses its own selection mechanism
    try {
      const selection = window.getSelection();
      return selection.toString();
    } catch (e) {
      return '';
    }
  }

  insertUI(element) {
    // Insert at the bottom right of the document
    element.style.position = 'fixed';
    element.style.bottom = '20px';
    element.style.right = '20px';
    element.style.zIndex = '99999';
    document.body.appendChild(element);
  }

  getMetadata() {
    const metadata = super.getMetadata();
    // Extract title from Google Docs header
    const titleElement = document.querySelector('[data-is-doc-title="true"]');
    if (titleElement) {
      metadata.title = titleElement.innerText;
    }
    // Try to extract owner/author
    metadata.documentId = this.extractDocumentId();
    return metadata;
  }

  extractDocumentId() {
    const match = window.location.pathname.match(/\/document\/d\/([a-zA-Z0-9-_]+)/);
    return match ? match[1] : null;
  }

  isApplicable() {
    return window.location.hostname.includes('docs.google.com');
  }
}

/**
 * Notion Adapter
 */
class NotionAdapter extends BasePlatformAdapter {
  constructor() {
    super();
    this.platformName = 'notion';
  }

  getTextContent() {
    // Notion stores content in several possible ways
    // Try to get from the main content area
    let content = '';

    // Method 1: Look for notion-scroller (main content area)
    const scroller = document.querySelector('[class*="notion-scroller"]');
    if (scroller) {
      content = scroller.innerText;
    }

    // Method 2: Fallback to all block content
    if (!content) {
      const blocks = document.querySelectorAll('[data-block-id]');
      const textArray = Array.from(blocks).map(block => block.innerText);
      content = textArray.join('\n');
    }

    return content;
  }

  insertUI(element) {
    // Notion pages have a sidebar area
    element.style.position = 'fixed';
    element.style.bottom = '20px';
    element.style.right = '20px';
    element.style.zIndex = '999999'; // Notion has high z-index items
    document.body.appendChild(element);
  }

  getMetadata() {
    const metadata = super.getMetadata();
    // Try to extract page title from Notion
    const titleElement = document.querySelector('h1');
    if (titleElement) {
      metadata.title = titleElement.innerText;
    }
    metadata.pageId = this.extractPageId();
    return metadata;
  }

  extractPageId() {
    // Notion page IDs are in the URL
    const match = window.location.pathname.match(/([a-f0-9]{32})/);
    return match ? match[1] : null;
  }

  isApplicable() {
    const hostname = window.location.hostname;
    return hostname.includes('notion.so') || hostname.includes('notion.com');
  }
}

/**
 * Obsidian Adapter (for Obsidian Publish or web version)
 */
class ObsidianAdapter extends BasePlatformAdapter {
  constructor() {
    super();
    this.platformName = 'obsidian';
  }

  getTextContent() {
    // Obsidian Publish pages
    const mainContent = document.querySelector('main') || document.querySelector('[role="main"]');
    return mainContent ? mainContent.innerText : document.body.innerText;
  }

  insertUI(element) {
    // Obsidian pages usually have a sidebar
    element.style.position = 'fixed';
    element.style.bottom = '20px';
    element.style.right = '20px';
    element.style.zIndex = '999999';
    document.body.appendChild(element);
  }

  getMetadata() {
    const metadata = super.getMetadata();
    // Try to get from document title or heading
    const heading = document.querySelector('h1');
    if (heading) {
      metadata.title = heading.innerText;
    }
    return metadata;
  }

  isApplicable() {
    return document.body.classList.contains('obsidian') || 
           window.location.hostname.includes('obsidian.md');
  }
}

/**
 * Roam Research Adapter
 */
class RoamResearchAdapter extends BasePlatformAdapter {
  constructor() {
    super();
    this.platformName = 'roam-research';
  }

  getTextContent() {
    // Roam stores content in roam-blocks
    const blocks = document.querySelectorAll('[class*="roam-block"]');
    const textArray = Array.from(blocks).map(block => block.innerText);
    return textArray.join('\n');
  }

  insertUI(element) {
    element.style.position = 'fixed';
    element.style.bottom = '20px';
    element.style.right = '20px';
    element.style.zIndex = '99999';
    document.body.appendChild(element);
  }

  isApplicable() {
    return window.location.hostname.includes('roamresearch.com');
  }
}

/**
 * OneNote Adapter
 */
class OneNoteAdapter extends BasePlatformAdapter {
  constructor() {
    super();
    this.platformName = 'onenote';
  }

  getTextContent() {
    // OneNote stores content in specific containers
    const content = document.querySelector('[id*="contentContainer"]');
    return content ? content.innerText : document.body.innerText;
  }

  insertUI(element) {
    element.style.position = 'fixed';
    element.style.bottom = '20px';
    element.style.right = '20px';
    element.style.zIndex = '99999';
    document.body.appendChild(element);
  }

  isApplicable() {
    return window.location.hostname.includes('onenote.com') ||
           window.location.hostname.includes('office.com');
  }
}

/**
 * Evernote Adapter
 */
class EvernoteAdapter extends BasePlatformAdapter {
  constructor() {
    super();
    this.platformName = 'evernote';
  }

  getTextContent() {
    const content = document.querySelector('[class*="note-content"]') ||
                    document.querySelector('[data-editor-type]');
    return content ? content.innerText : document.body.innerText;
  }

  insertUI(element) {
    element.style.position = 'fixed';
    element.style.bottom = '20px';
    element.style.right = '20px';
    element.style.zIndex = '99999';
    document.body.appendChild(element);
  }

  isApplicable() {
    return window.location.hostname.includes('evernote.com');
  }
}

/**
 * Confluence Adapter
 */
class ConfluenceAdapter extends BasePlatformAdapter {
  constructor() {
    super();
    this.platformName = 'confluence';
  }

  getTextContent() {
    // Confluence stores content in the main page area
    const content = document.querySelector('[id*="main-content"]') ||
                    document.querySelector('[class*="page-content"]');
    return content ? content.innerText : document.body.innerText;
  }

  insertUI(element) {
    element.style.position = 'fixed';
    element.style.bottom = '20px';
    element.style.right = '20px';
    element.style.zIndex = '99999';
    document.body.appendChild(element);
  }

  isApplicable() {
    const hostname = window.location.hostname;
    return hostname.includes('confluence') || hostname.includes('atlassian.net');
  }
}

/**
 * Generic Editor Adapter
 * Fallback for any contentEditable element
 */
class GenericEditorAdapter extends BasePlatformAdapter {
  constructor() {
    super();
    this.platformName = 'generic-editor';
  }

  getTextContent() {
    // Get all contentEditable elements
    const editables = document.querySelectorAll('[contenteditable="true"]');
    const textArray = Array.from(editables).map(el => el.innerText);
    return textArray.join('\n');
  }

  insertUI(element) {
    element.style.position = 'fixed';
    element.style.bottom = '20px';
    element.style.right = '20px';
    element.style.zIndex = '99999';
    document.body.appendChild(element);
  }

  isApplicable() {
    return PlatformDetector.hasContentEditable();
  }
}

/**
 * Adapter for scientific papers and general web pages
 */
class ScientificPaperAdapter extends BasePlatformAdapter {
  constructor() {
    super();
    this.platformName = 'scientific-paper';
  }

  getTextContent() {
    let text = '';
    
    // Method 1: Try scientific article selectors first
    const scienceSelectors = [
      'article',                    // Generic article tag
      '.c-article-body',           // Common science journal class  
      '.article-body',
      '.content-body',
      '#article-content',
      '[data-track="article-body"]',
      '.main-content',
      '[role="article"]',
      '.article__body',
      '#main-content'
    ];
    
    for (const selector of scienceSelectors) {
      const element = document.querySelector(selector);
      if (element && element.innerText && element.innerText.trim().length > 200) {
        text = element.innerText;
        console.log(`[ScientificPaperAdapter] Found text via selector: ${selector}, length: ${text.length}`);
        return text.trim();
      }
    }
    
    // Method 2: Try main content areas
    const mainSelectors = ['main', '[role="main"]', '.content', '#content'];
    for (const selector of mainSelectors) {
      const element = document.querySelector(selector);
      if (element && element.innerText && element.innerText.trim().length > 200) {
        text = element.innerText;
        console.log(`[ScientificPaperAdapter] Found text via main selector: ${selector}, length: ${text.length}`);
        return text.trim();
      }
    }
    
    // Method 3: Try paragraphs
    const paragraphs = document.querySelectorAll('p');
    if (paragraphs.length > 0) {
      text = Array.from(paragraphs).map(p => p.innerText).filter(t => t.trim().length > 0).join('\n');
      if (text.trim().length > 100) {
        console.log(`[ScientificPaperAdapter] Found text via paragraphs: ${paragraphs.length} paragraphs, total length: ${text.length}`);
        return text.trim();
      }
    }
    
    // Method 4: Last resort - get body text  
    text = document.body.innerText || document.body.textContent || '';
    console.log(`[ScientificPaperAdapter] Using body text as fallback, length: ${text.length}`);
    return text.trim();
  }

  insertUI(element) {
    element.style.position = 'fixed';
    element.style.bottom = '20px';
    element.style.right = '20px';
    element.style.zIndex = '99999';
    document.body.appendChild(element);
  }

  isApplicable() {
    return true; // Always applicable as fallback
  }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PlatformDetector;
}
