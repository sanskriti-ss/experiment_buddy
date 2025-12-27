"""
Experiment Buddy - FastAPI Backend Server

This server provides API endpoints for the Chrome extension to analyze
experimental procedures from note-taking platforms like Google Docs, Notion, etc.
"""

import os
import json
from typing import Optional
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
        
        # Analyze completeness of each step
        analysis = analyze_procedure_completeness(procedure_ir)
        
        return {
            "success": True,
            "procedure_ir": procedure_ir,
            "analysis": analysis,
            "validation_errors": validation_errors,
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
            "validation_errors": validation_errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error extracting paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= Helper Functions =============

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
        
        # Check what's missing
        missing = ActionRequirements.check_missing_params(action, params)
        score = ActionRequirements.get_completeness_score(action, params)
        
        step_analysis = {
            "id": step.get("id", ""),
            "action": action,
            "text": step.get("raw_text", "")[:100] + "..." if len(step.get("raw_text", "")) > 100 else step.get("raw_text", ""),
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
    ║          🔬 Experiment Buddy API Server                  ║
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
