"""
Fetch and extract Methods sections from scientific papers using LLM + web search.

This module uses the Dedalus API (which provides access to LLMs and Exa search)
to intelligently fetch paper content and locate relevant methodology sections.
"""

import os
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class PaperContent:
    """Structured representation of extracted paper content."""
    url: str
    citation: Optional[str]
    methods_text: str
    section_name: str  # e.g., "Methods", "Materials and Methods", etc.
    full_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaperFetcher:
    """
    Fetch scientific papers and extract Methods sections.
    
    Uses LLM + web search to handle various paper formats (HTML, PDF, paywalls).
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-4o-mini"):
        """
        Initialize the fetcher.
        
        Args:
            api_key: Dedalus API key (if None, reads from DEDALUS_API_KEY env var)
            model: LLM model to use for content extraction
        """
        self.api_key = api_key or os.getenv('DEDALUS_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Dedalus API key required. Set DEDALUS_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.model = model
        
    async def fetch_paper_async(self, url: str) -> PaperContent:
        """
        Fetch a paper and extract its Methods section (async version).
        
        Args:
            url: URL to the paper (DOI, PubMed, arXiv, journal URL, etc.)
            
        Returns:
            PaperContent with extracted methods text
            
        Raises:
            ValueError: If URL is invalid or paper cannot be fetched
            RuntimeError: If Methods section cannot be located
        """
        from dedalus_labs import AsyncDedalus, DedalusRunner
        
        # Normalize URL (handle DOI, PMID, etc.)
        normalized_url = self._normalize_url(url)
        
        # Create Dedalus client and runner
        client = AsyncDedalus(api_key=self.api_key)
        runner = DedalusRunner(client)
        
        # Step 1: Fetch paper content using web search MCP
        fetch_prompt = self._build_fetch_prompt(normalized_url)
        
        try:
            # Try Brave Search MCP first (better for content extraction)
            # Then fall back to Exa
            mcp_attempts = [
                ("tsion/brave-search-mcp", "Brave Search"),
                ("joerup/exa-mcp", "Exa")
            ]
            
            paper_text = None
            errors = []
            
            for mcp_server, name in mcp_attempts:
                try:
                    fetch_response = await runner.run(
                        input=fetch_prompt,
                        model=self.model,
                        mcp_servers=[mcp_server]
                    )
                    paper_text = fetch_response.final_output
                    
                    # Check if we got actual content
                    if paper_text and len(paper_text) > 500:
                        break
                    else:
                        errors.append(f"{name}: only {len(paper_text) if paper_text else 0} chars")
                except Exception as e:
                    errors.append(f"{name}: {str(e)}")
                    continue
            
            if not paper_text or len(paper_text) < 500:
                raise RuntimeError(
                    f"Could not fetch sufficient paper content. Attempts: {'; '.join(errors)}. "
                    f"\n\nRECOMMENDATION: Use 'extract-text' command instead:\n"
                    f"  1. Open {normalized_url} in browser\n"
                    f"  2. Copy Methods section to a text file\n"
                    f"  3. Run: python3 -m planlint.cli extract-text methods.txt"
                )
            
            # Step 2: Extract Methods section using LLM
            extract_prompt = self._build_extraction_prompt(paper_text, normalized_url)
            extract_response = await runner.run(
                input=extract_prompt,
                model=self.model
            )
            
            # Parse the LLM response to get structured content
            return self._parse_extraction_response(
                extract_response.final_output,
                normalized_url,
                paper_text
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch or extract paper: {e}") from e
    
    def fetch_paper(self, url: str) -> PaperContent:
        """
        Fetch a paper and extract its Methods section (sync wrapper).
        
        Args:
            url: URL to the paper
            
        Returns:
            PaperContent with extracted methods text
        """
        import asyncio
        return asyncio.run(self.fetch_paper_async(url))
    
    def _normalize_url(self, url: str) -> str:
        """Convert DOI, PMID, etc. into full URLs."""
        url = url.strip()
        
        # Handle DOI
        if url.startswith('10.') or url.startswith('doi:'):
            doi = url.replace('doi:', '').strip()
            return f'https://doi.org/{doi}'
        
        # Handle PubMed ID
        if url.startswith('PMID:') or url.startswith('pmid:'):
            pmid = url.replace('PMID:', '').replace('pmid:', '').strip()
            return f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
        
        # Handle arXiv ID
        if url.startswith('arXiv:') or url.startswith('arxiv:'):
            arxiv_id = url.replace('arXiv:', '').replace('arxiv:', '').strip()
            return f'https://arxiv.org/abs/{arxiv_id}'
        
        # If it's just a number and looks like PMID
        if url.isdigit() and len(url) >= 7:
            return f'https://pubmed.ncbi.nlm.nih.gov/{url}/'
        
        # Otherwise assume it's already a URL
        if not url.startswith('http'):
            url = 'https://' + url
            
        return url
    
    def _build_fetch_prompt(self, url: str) -> str:
        """Build prompt for fetching paper content."""
        return f"""I need the FULL TEXT CONTENT of this webpage: {url}

TASK: Fetch and return the complete text content from this URL.

This is a scientific paper page. I need:
- The complete article text (not just abstract)
- All sections including Methods/Materials and Methods
- The raw text content as it appears on the page

URL: {url}

Please fetch this page and return ALL the text content you can access."""
    
    def _build_extraction_prompt(self, paper_text: str, url: str) -> str:
        """Build prompt for extracting Methods section."""
        return f"""Extract the Methods section from this scientific paper.

Paper URL: {url}

Paper text:
{paper_text}

Your task:
1. Identify the section containing experimental methods (it may be called "Methods", "Materials and Methods", "Experimental Procedures", "Methods and Materials", etc.)
2. Extract the COMPLETE text of that section
3. If there are subsections (e.g., "Cell Culture", "Microscopy", "Image Analysis"), include ALL of them
4. If methods are split across multiple sections (e.g., main text + supplement), note that

Respond in this exact format:

SECTION_NAME: <the actual heading of the methods section>
CITATION: <extract DOI or citation if visible, otherwise say "Not found">
---METHODS_START---
<full methods text here, preserving all details>
---METHODS_END---

If you cannot find a methods section, respond with:
ERROR: No methods section found"""
    
    def _parse_extraction_response(
        self,
        llm_response: str,
        url: str,
        full_text: str
    ) -> PaperContent:
        """Parse the LLM's extraction response into structured PaperContent."""
        
        if "ERROR:" in llm_response or "No methods section found" in llm_response:
            raise RuntimeError(
                f"Could not locate Methods section in paper at {url}. "
                f"LLM response: {llm_response[:200]}"
            )
        
        # Extract section name
        section_match = re.search(r'SECTION_NAME:\s*(.+?)(?:\n|$)', llm_response)
        section_name = section_match.group(1).strip() if section_match else "Methods"
        
        # Extract citation
        citation_match = re.search(r'CITATION:\s*(.+?)(?:\n|$)', llm_response)
        citation = citation_match.group(1).strip() if citation_match else None
        if citation and citation.lower() == "not found":
            citation = None
        
        # Extract methods text
        methods_match = re.search(
            r'---METHODS_START---\s*(.+?)\s*---METHODS_END---',
            llm_response,
            re.DOTALL
        )
        
        if not methods_match:
            raise RuntimeError(
                f"Could not parse Methods section from LLM response. "
                f"Response format was unexpected."
            )
        
        methods_text = methods_match.group(1).strip()
        
        if len(methods_text) < 50:
            raise RuntimeError(
                f"Extracted Methods section is suspiciously short ({len(methods_text)} chars). "
                "Extraction may have failed."
            )
        
        return PaperContent(
            url=url,
            citation=citation,
            methods_text=methods_text,
            section_name=section_name,
            full_text=full_text,
            metadata={
                'methods_length': len(methods_text),
                'full_text_length': len(full_text)
            }
        )
