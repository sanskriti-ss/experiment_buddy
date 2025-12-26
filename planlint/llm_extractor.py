"""
Extract structured procedure IR from free-text Methods sections using LLM.

This module converts unstructured protocol text into the procedure_ir_v0 schema,
identifying steps, actions, parameters, and missing required information.
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class LLMExtractor:
    """
    Extract structured procedure information from Methods text using LLM.
    
    Converts free-text protocols into procedure_ir_v0 JSON schema.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-4o-mini"):
        """
        Initialize the extractor.
        
        Args:
            api_key: Dedalus API key (if None, reads from DEDALUS_API_KEY env var)
            model: LLM model to use for extraction
        """
        self.api_key = api_key or os.getenv('DEDALUS_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Dedalus API key required. Set DEDALUS_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.model = model
        
    async def extract_procedure_async(
        self,
        methods_text: str,
        source_type: str = "methods_section",
        citation: Optional[str] = None,
        url: Optional[str] = None,
        section_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured procedure IR from methods text (async).
        
        Args:
            methods_text: The raw methods/procedure text
            source_type: Type of source (methods_section, supplement, etc.)
            citation: Optional citation/DOI
            url: Optional URL to source
            section_name: Optional name of the section (e.g., "Materials and Methods")
            
        Returns:
            Dictionary conforming to procedure_ir_v0 schema
            
        Raises:
            ValueError: If extraction fails or produces invalid JSON
        """
        from dedalus_labs import AsyncDedalus, DedalusRunner
        
        client = AsyncDedalus(api_key=self.api_key)
        runner = DedalusRunner(client)
        
        prompt = self._build_extraction_prompt(methods_text)
        
        try:
            response = await runner.run(
                input=prompt,
                model=self.model
            )
            
            # Parse JSON from LLM response
            procedure_ir = self._parse_llm_response(response.final_output)
            
            # Add source metadata
            procedure_ir["source"] = {
                "type": source_type,
                "text": methods_text
            }
            
            if citation:
                procedure_ir["source"]["citation"] = citation
            if url:
                procedure_ir["source"]["url"] = url
            if section_name:
                procedure_ir["source"]["section"] = section_name
            
            # Add extraction metadata
            procedure_ir["extraction_metadata"] = {
                "extractor_name": "dedalus-llm-extractor",
                "extractor_version": "0.1.0",
                "model": self.model,
                "extraction_timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            return procedure_ir
            
        except Exception as e:
            raise ValueError(f"Failed to extract procedure: {e}") from e
    
    def extract_procedure(
        self,
        methods_text: str,
        source_type: str = "methods_section",
        citation: Optional[str] = None,
        url: Optional[str] = None,
        section_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured procedure IR from methods text (sync wrapper).
        
        Args:
            methods_text: The raw methods/procedure text
            source_type: Type of source
            citation: Optional citation/DOI
            url: Optional URL to source
            section_name: Optional section name
            
        Returns:
            Dictionary conforming to procedure_ir_v0 schema
        """
        import asyncio
        return asyncio.run(
            self.extract_procedure_async(
                methods_text, source_type, citation, url, section_name
            )
        )
    
    def _build_extraction_prompt(self, methods_text: str) -> str:
        """Build the prompt for LLM extraction."""
        
        schema_example = {
            "schema_version": "procedure_ir_v0",
            "source": {
                "type": "methods_section",
                "text": "..."
            },
            "steps": [
                {
                    "id": "step_1",
                    "raw_text": "Cells were fixed in 4% paraformaldehyde for 15 min at room temperature.",
                    "action": "fix",
                    "parameters": [
                        {
                            "name": "fixative",
                            "value": "paraformaldehyde",
                            "unit": "percent",
                        },
                        {
                            "name": "fixative_concentration",
                            "value": 4,
                            "unit": "percent"
                        },
                        {
                            "name": "duration_min",
                            "value": 15,
                            "unit": "minutes"
                        },
                        {
                            "name": "temperature",
                            "value": "room temperature",
                            "unit": "ambient"
                        }
                    ],
                    "missing_required": ["fixative_volume", "wash_steps_after"],
                    "confidence": 0.95
                }
            ]
        }
        
        return f"""You are an expert at extracting structured experimental protocols from scientific papers.

Your task: Convert this Methods section into structured JSON following the procedure_ir_v0 schema.

Methods text:
```
{methods_text}
```

Instructions:
1. Break the text into individual procedural steps
2. For each step:
   - Assign a unique id (step_1, step_2, etc.)
   - Extract the raw text for that step
   - Classify the action type (fix, stain, wash, incubate, image, etc.)
   - Extract all parameters with values and units:
     * Time: duration_min, duration_h
     * Temperature: temperature_c, temperature (if "room temp" or "RT")
     * Concentrations: concentration_uM, concentration_percent, dilution_ratio
     * Microscopy: objective_magnification, objective_na, exposure_ms, laser_power_mw, wavelength_nm, z_step_um, xy_pixel_size_um
     * Volumes: volume_ul, volume_ml
   - Identify MISSING required parameters (see below for what each action requires)
   - Assign confidence (0-1) based on how clearly the step is specified

3. Required parameters by action type:
   - fix: fixative, concentration, duration, temperature, wash_steps
   - stain: reagent_name, concentration_or_dilution, duration, temperature
   - wash: wash_buffer, number_of_washes, duration_per_wash
   - incubate: duration, temperature, conditions (e.g., humidity, CO2)
   - image: microscope_type, objective_magnification, objective_na, channels/wavelengths, exposure_time, z_step (if z-stack), pixel_size
   - mount: mounting_medium, coverslip_info
   - permeabilize: detergent, concentration, duration
   - block: blocking_agent, concentration, duration, temperature

4. If a parameter is mentioned but not quantified (e.g., "cells were washed"), include it with value=null and list the specific missing info in missing_required

Output ONLY valid JSON matching this schema. No extra text before or after.

Example output structure:
```json
{schema_example}
```

Now extract the procedure from the provided Methods text:"""
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate LLM response as JSON."""
        
        # Try to extract JSON from markdown code blocks if present
        json_match = response.strip()
        if '```json' in json_match:
            json_match = json_match.split('```json')[1].split('```')[0]
        elif '```' in json_match:
            json_match = json_match.split('```')[1].split('```')[0]
        
        json_match = json_match.strip()
        
        try:
            procedure_ir = json.loads(json_match)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM response was not valid JSON. Error: {e}\n"
                f"Response preview: {response[:500]}"
            ) from e
        
        # Basic validation
        if not isinstance(procedure_ir, dict):
            raise ValueError("Extracted procedure is not a JSON object")
        
        if "steps" not in procedure_ir:
            raise ValueError("Extracted procedure missing 'steps' field")
        
        if not isinstance(procedure_ir["steps"], list):
            raise ValueError("'steps' field must be an array")
        
        if len(procedure_ir["steps"]) == 0:
            raise ValueError("Extracted procedure has no steps")
        
        # Ensure schema_version is set
        procedure_ir["schema_version"] = "procedure_ir_v0"
        
        return procedure_ir
