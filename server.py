"""
Experiment Buddy - FastAPI Backend Server

This server provides API endpoints for the Chrome extension to analyze
experimental procedures from note-taking platforms like Google Docs, Notion, etc.
"""

import os
import json
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import planlint modules
from planlint.llm_extractor import LLMExtractor
from planlint.procedure_validator import ProcedureValidator
from planlint.action_requirements import ActionRequirements

app = FastAPI(
    title="Experiment Buddy API",
    description="Analyze experimental procedures for reproducibility gaps",
    version="1.0.0"
)

# Enable CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= Request/Response Models =============

class ContentAnalysis(BaseModel):
    """Analysis of the submitted text content"""
    wordCount: int = 0
    foundKeywordCount: int = 0
    hasExperimentalContent: bool = False
    keywords: list[str] = []
    isLikelyProcedure: bool = False


class DocumentMetadata(BaseModel):
    """Metadata about the source document"""
    title: Optional[str] = None
    url: Optional[str] = None
    platform: Optional[str] = None
    documentId: Optional[str] = None


class ExtractRequest(BaseModel):
    """Request to extract and analyze a procedure from text"""
    text: str
    source: str = "unknown"  # 'selected', 'full-document', 'identified-procedure'
    metadata: Optional[DocumentMetadata] = None
    contentAnalysis: Optional[ContentAnalysis] = None
    model: str = "openai/gpt-4o-mini"


class PaperRequest(BaseModel):
    """Request to extract procedure from a paper URL"""
    url: str
    model: str = "openai/gpt-4o-mini"


# ============= API Endpoints =============

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Experiment Buddy API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/extract": "Extract procedure from text (POST)",
            "/extract-paper": "Extract procedure from paper URL (POST)",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


def make_errors_user_friendly(validation_errors: List[str]) -> List[str]:
    """Convert technical validation errors to user-friendly descriptions."""
    if not validation_errors:
        return []
    
    user_friendly = []
    
    for error in validation_errors:
        # Parse common error patterns and make them readable
        if "'add' is not one of" in error:
            user_friendly.append("Step uses 'add' action - this should be changed to 'add_reagent' for adding chemicals/reagents")
        elif "'replace' is not one of" in error:
            user_friendly.append("Step uses 'replace' action - this should be changed to 'aspirate' + 'add_reagent' for medium changes")
        elif "'seed' is not one of" in error:
            user_friendly.append("Step uses 'seed' action - this is now supported for cell seeding procedures")
        elif "'media_change' is not one of" in error:
            user_friendly.append("Step uses 'media_change' action - this is now supported for cell culture protocols")
        elif "'extract' is not one of" in error:
            user_friendly.append("Step uses 'extract' action - this is now supported for sample extraction procedures")
        elif "is not one of" in error and "action" in error:
            # Extract the action name from error message
            parts = error.split("'")
            if len(parts) >= 2:
                action = parts[1]
                user_friendly.append(f"Step uses '{action}' action - consider using a more specific action type like 'add_reagent', 'incubate', 'wash', etc.")
            else:
                user_friendly.append("Step uses an unrecognized action type - check if a more specific action would be appropriate")
        elif "temperature" in error.lower():
            user_friendly.append("Temperature information is missing or unclear - specify exact temperature with units (°C)")
        elif "duration" in error.lower():
            user_friendly.append("Time duration is missing or unclear - specify exact timing (e.g., '30 minutes', '2 hours')")
        elif "concentration" in error.lower():
            user_friendly.append("Reagent concentration is missing - specify exact amounts and units (e.g., '10 μM', '2 mg/ml')")
        elif "volume" in error.lower():
            user_friendly.append("Volume information is missing - specify exact volumes (e.g., '500 μl', '2 ml')")
        elif "required" in error.lower():
            user_friendly.append("Required information is missing from this step - check that all essential details are included")
        else:
            # For other errors, try to make them more readable
            clean_error = error.replace("Error at steps -> ", "Step ")
            clean_error = clean_error.replace(" -> ", " ")
            clean_error = clean_error.replace("Error: ", "")
            user_friendly.append(f"Issue: {clean_error}")
            clean_error = error.replace("Error at steps -> ", "Step ")
            clean_error = clean_error.replace(" -> ", " ")
            clean_error = clean_error.replace("Error: ", "")
            user_friendly.append(f"Warning: {clean_error}")
    
    return user_friendly


@app.post("/extract")
async def extract_procedure(request: ExtractRequest):
    """
    Extract and analyze experimental procedure from text.
    
    This endpoint receives text from the Chrome extension (from Google Docs,
    Notion, etc.) and returns a structured analysis of the experimental procedure.
    """
    try:
        text = request.text.strip()
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        if len(text) < 50:
            raise HTTPException(
                status_code=400, 
                detail="Text too short. Please provide more content for analysis."
            )
        
        # Extract procedure using LLM
        extractor = LLMExtractor(model=request.model)
        
        # First check if this is a review article
        review_check = await check_if_review_article(text, extractor)
        
        if review_check.get("is_review", False) and review_check.get("confidence", 0) > 0.7:
            return {
                "success": False,
                "error": "review_article_detected",
                "message": review_check.get("reason", "This appears to be a review article"),
                "suggestion": review_check.get("suggestion", "Please select a Methods section from an original research paper"),
                "review_check": review_check,
                "metadata": {
                    "source": request.source,
                    "platform": request.metadata.platform if request.metadata else None,
                    "model": request.model,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        # Build citation from metadata
        citation = None
        if request.metadata:
            citation = request.metadata.title or "Document"
            if request.metadata.platform:
                citation += f" ({request.metadata.platform})"
        
        # Extract procedure IR from text
        procedure_ir = await extractor.extract_procedure_async(
            methods_text=text,
            source_type=request.source,
            citation=citation,
            url=request.metadata.url if request.metadata else None,
            section_name=request.source
        )
        
        # Validate the extracted procedure
        validator = ProcedureValidator()
        validation_errors = validator.validate(procedure_ir)
        user_friendly_errors = make_errors_user_friendly(validation_errors)
        
        # Analyze completeness of each step
        analysis = analyze_procedure_completeness(procedure_ir)
        
        # Add replicability gap analysis as fallback when procedures don't match specific schemas
        # This provides LLM-based analysis for domain-specific replicability issues
        replicability_gaps = await analyze_replicability_gaps(text, extractor)
        
        return {
            "success": True,
            "procedure_ir": procedure_ir,
            "analysis": analysis,
            "validation_errors": user_friendly_errors,
            "replicability_gaps": replicability_gaps,
            "technical_errors": validation_errors,  # Keep technical errors for debugging
            "metadata": {
                "source": request.source,
                "platform": request.metadata.platform if request.metadata else None,
                "model": request.model,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error extracting procedure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-paper")
async def extract_paper_procedure(request: PaperRequest):
    """
    Extract procedure from a scientific paper URL.
    
    This endpoint fetches a paper from a URL (DOI, PubMed, arXiv, etc.),
    extracts the Methods section, and analyzes it.
    """
    try:
        from planlint.paper_fetcher import PaperFetcher
        
        # Fetch the paper
        fetcher = PaperFetcher(model=request.model)
        paper = fetcher.fetch_paper(request.url)
        
        if not paper or not paper.get("methods_text"):
            raise HTTPException(
                status_code=404, 
                detail="Could not extract methods section from paper"
            )
        
        # Extract procedure
        extractor = LLMExtractor(model=request.model)
        procedure_ir = await extractor.extract_procedure_async(
            methods_text=paper["methods_text"],
            source_type="paper",
            citation=paper.get("citation"),
            url=paper.get("url"),
            section_name=paper.get("section_name", "Methods")
        )
        
        # Validate
        validator = ProcedureValidator()
        validation_errors = validator.validate(procedure_ir)
        user_friendly_errors = make_errors_user_friendly(validation_errors)
        
        # Analyze completeness
        analysis = analyze_procedure_completeness(procedure_ir)
        
        return {
            "success": True,
            "paper": {
                "url": paper.get("url"),
                "citation": paper.get("citation"),
                "section": paper.get("section_name")
            },
            "procedure_ir": procedure_ir,
            "analysis": analysis,
            "validation_errors": user_friendly_errors,
            "technical_errors": validation_errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error extracting paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= Helper Functions =============

async def analyze_replicability_gaps(text: str, extractor: LLMExtractor) -> List[str]:
    """
    Use LLM to identify specific replicability gaps in methodology text.
    
    This function provides a fallback analysis when structured JSON validation
    doesn't capture domain-specific replicability issues.
    """
    replicability_prompt = f"""You are an expert in research methodology and reproducibility. Analyze the following experimental methods section and identify specific details that are missing or unclear, which would prevent another researcher from replicating this work.

Focus on practical, actionable feedback. For each issue you identify, explain what specific information needs to be added or clarified.

Methods text to analyze:
{text}

Please provide a concise list of missing or unclear details that impact replicability. For each item, be specific about:
1. What information is missing
2. Why it's needed for replication
3. What should be specified instead

Format your response as a JSON array of strings, where each string describes one specific replicability gap. Example:
[
  "Cell seeding density not specified - need exact number of cells per well for consistent results",
  "Antibody incubation temperature missing - primary antibody effectiveness varies significantly with temperature",
  "Centrifugation speed not provided - different speeds will affect cell pellet formation and viability"
]

Be thorough but concise. Focus on the most critical gaps that would prevent successful replication."""

    try:
        from dedalus_labs import AsyncDedalus, DedalusRunner
        
        client = AsyncDedalus(api_key=extractor.api_key)
        runner = DedalusRunner(client)
        
        response = await runner.run(
            input=replicability_prompt,
            model=extractor.model
        )
        
        # Parse JSON response
        gaps_text = response.final_output.strip()
        
        # Extract JSON array from response
        import re
        json_match = re.search(r'\[.*?\]', gaps_text, re.DOTALL)
        if json_match:
            gaps = json.loads(json_match.group())
            return gaps if isinstance(gaps, list) else []
        else:
            # Fallback: split by lines and clean up
            lines = gaps_text.split('\n')
            gaps = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('[') and not line.startswith(']'):
                    # Remove bullet points, numbers, quotes
                    line = re.sub(r'^[\d\.\-\*\"\s]+', '', line)
                    line = line.strip('\'"')
                    if line:
                        gaps.append(line)
            return gaps[:10]  # Limit to 10 most important gaps
            
    except Exception as e:
        print(f"Error in replicability analysis: {e}")
        return ["Unable to analyze replicability gaps - please check methodology manually"]


async def check_if_review_article(text: str, extractor: LLMExtractor) -> dict:
    """
    Check if the content is a review article rather than containing actual methods.
    
    Returns a dictionary with:
    - is_review: bool
    - confidence: float (0-1)
    - reason: str
    - suggestion: str
    """
    review_check_prompt = f"""You are an expert at distinguishing between different types of scientific content. Analyze the following text and determine if this is a review article or if it contains actual experimental methodology.

Text to analyze:
{text[:2000]}...

Please determine:
1. Is this primarily a review article that summarizes and discusses other research?
2. Does it contain actual step-by-step experimental procedures that could be replicated?
3. What type of content is this?

Respond in this exact JSON format:
{{
  "is_review": true/false,
  "confidence": 0.0-1.0,
  "content_type": "review_article" | "methods_section" | "introduction" | "discussion" | "mixed_content",
  "reason": "Brief explanation of why you classified it this way",
  "suggestion": "What the user should do instead (if it's a review)"
}}

Examples:
- If text discusses "methods have been developed" or "studies have shown" → likely review
- If text says "we cultured cells" or "samples were incubated" → likely methods
- If text explains background without procedures → likely introduction/review"""

    try:
        from dedalus_labs import AsyncDedalus, DedalusRunner
        
        client = AsyncDedalus(api_key=extractor.api_key)
        runner = DedalusRunner(client)
        
        response = await runner.run(
            input=review_check_prompt,
            model=extractor.model
        )
        
        # Parse JSON response
        import re
        json_match = re.search(r'\{.*?\}', response.final_output, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            return {
                "is_review": False,
                "confidence": 0.5,
                "content_type": "unknown",
                "reason": "Could not parse LLM response",
                "suggestion": "Try selecting a clear Methods section"
            }
            
    except Exception as e:
        print(f"Error in review article check: {e}")
        return {
            "is_review": False,
            "confidence": 0.5,
            "content_type": "unknown", 
            "reason": f"Analysis failed: {str(e)}",
            "suggestion": "Try selecting a clear Methods section"
        }


def analyze_procedure_completeness(procedure_ir: dict) -> dict:
    """
    Analyze the completeness of an extracted procedure.
    
    Returns statistics about which steps are complete and which are missing
    required parameters for reproducibility.
    """
    steps = procedure_ir.get("steps", [])
    
    analysis = {
        "total_steps": len(steps),
        "complete_steps": 0,
        "incomplete_steps": 0,
        "overall_score": 0.0,
        "steps": []
    }
    
    if not steps:
        return analysis
    
    total_score = 0.0
    
    for step in steps:
        action = step.get("action", "unknown")
        params = [p.get("name", "") for p in step.get("parameters", [])]
        raw_text = step.get("raw_text", "")
        
        # Check what's missing
        missing = ActionRequirements.check_missing_params(action, params)
        score = ActionRequirements.get_completeness_score(action, params, raw_text)
        
        step_analysis = {
            "id": step.get("id", ""),
            "action": action,
            "text": raw_text[:100] + "..." if len(raw_text) > 100 else raw_text,
            "parameters_found": len(params),
            "missing_parameters": missing,
            "completeness_score": score,
            "is_complete": len(missing) == 0
        }
        
        if len(missing) == 0:
            analysis["complete_steps"] += 1
        else:
            analysis["incomplete_steps"] += 1
        
        total_score += score
        analysis["steps"].append(step_analysis)
    
    # Calculate overall score
    analysis["overall_score"] = round(total_score / len(steps), 2) if steps else 0.0
    
    return analysis


# ============= Main Entry Point =============

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Experiment Buddy API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║          Experiment Buddy API Server                     ║
    ╠══════════════════════════════════════════════════════════╣
    ║  Server running at: http://{args.host}:{args.port}                 ║
    ║  API docs at:       http://{args.host}:{args.port}/docs            ║
    ║  Health check:      http://{args.host}:{args.port}/health          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )
