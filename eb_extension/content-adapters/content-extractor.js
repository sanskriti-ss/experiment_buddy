/**
 * Content Extractor
 * Intelligently extracts relevant content from documents
 * Identifies potential experimental text that should be analyzed
 */

class ContentExtractor {
  constructor(adapter) {
    this.adapter = adapter;
  }

  /**
   * Extract all text from the document
   * @returns {string} Full document text
   */
  extractFullText() {
    return this.adapter.getTextContent();
  }

  /**
   * Extract selected text by user
   * @returns {string} Selected text or null
   */
  extractSelectedText() {
    const selected = this.adapter.getSelectedText();
    return selected && selected.trim().length > 0 ? selected : null;
  }

  /**
   * Extract text intelligently based on context
   * Uses heuristics to identify experimental procedure sections
   * @returns {string} Relevant text
   */
  extractRelevantText() {
    // First, try to get user selection
    const selectedText = this.extractSelectedText();
    if (selectedText) {
      return selectedText;
    }

    // Otherwise, try to identify procedure/methods sections
    const fullText = this.extractFullText();
    return this.identifyProcedureSection(fullText);
  }

  /**
   * Identify sections that look like experimental procedures
   * Uses pattern matching for common section headers
   * @param {string} text - Full document text
   * @returns {string} Identified procedure section
   */
  identifyProcedureSection(text) {
    const procedurePatterns = [
      /##?\s+(methods|methodology|procedure|protocol|experimental|techniques?)\s*\n([\s\S]*?)(?=\n##|$)/i,
      /##?\s+(materials?\s+and\s+)?methods?\s*\n([\s\S]*?)(?=\n##|$)/i,
      /##?\s+experimental\s+(design|procedure|setup)\s*\n([\s\S]*?)(?=\n##|$)/i,
      /\*\*methods?\*\*\s*\n([\s\S]*?)(?=\n\*\*|$)/i,
      /methods?\s*:\s*\n([\s\S]*?)(?=\n[^:]|$)/i,
    ];

    for (const pattern of procedurePatterns) {
      const match = text.match(pattern);
      if (match) {
        const section = match[match.length - 1];
        // Return the section if it's substantial (more than 100 chars)
        if (section.trim().length > 100) {
          return section;
        }
      }
    }

    // If no pattern matches, return the whole text
    // The backend will filter for relevance
    return text;
  }

  /**
   * Extract metadata about the document
   * @returns {Object} Metadata including title, URL, platform, etc.
   */
  getDocumentMetadata() {
    return this.adapter.getMetadata();
  }

  /**
   * Clean up text for processing
   * Remove extra whitespace, normalize line breaks
   * @param {string} text - Raw text
   * @returns {string} Cleaned text
   */
  static cleanText(text) {
    if (!text) return '';

    return text
      // Remove multiple spaces
      .replace(/  +/g, ' ')
      // Remove multiple line breaks
      .replace(/\n\n\n+/g, '\n\n')
      // Trim each line
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .join('\n')
      .trim();
  }

  /**
   * Estimate document word count
   * @param {string} text - Document text
   * @returns {number} Approximate word count
   */
  static getWordCount(text) {
    if (!text) return 0;
    return text.split(/\s+/).length;
  }

  /**
   * Check if text looks like it contains experimental content
   * @param {string} text - Document text
   * @returns {Object} Analysis results
   */
  static analyzeTextContent(text) {
    const cleaned = this.cleanText(text);
    const wordCount = this.getWordCount(cleaned);

    // Look for experimental keywords
    const experimentalKeywords = [
      'sample', 'method', 'procedure', 'protocol', 'experiment',
      'measurement', 'analyze', 'incubate', 'stain', 'wash',
      'image', 'microscop', 'temperature', 'time', 'concentration',
      'replicate', 'control', 'calibrate', 'quantif'
    ];

    const foundKeywords = experimentalKeywords.filter(keyword =>
      cleaned.toLowerCase().includes(keyword)
    );

    return {
      wordCount,
      foundKeywordCount: foundKeywords.length,
      hasExperimentalContent: foundKeywords.length >= 3,
      keywords: foundKeywords,
      isLikelyProcedure: wordCount > 200 && foundKeywords.length >= 3,
    };
  }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ContentExtractor;
}
