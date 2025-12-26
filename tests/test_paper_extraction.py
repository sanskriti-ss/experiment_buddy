"""
Tests for procedure extraction and analysis from papers.

These tests use mocked LLM responses to test the extraction pipeline
without requiring actual API calls.
"""

import json
import pytest
from pathlib import Path

from planlint.procedure_validator import ProcedureValidator
from planlint.action_requirements import ActionRequirements


class TestProcedureValidator:
    """Test procedure IR validation."""
    
    def test_validate_example_procedure(self):
        """Test that the example procedure IR validates correctly."""
        # Load example
        example_path = Path(__file__).parent.parent / "examples" / "procedure_ir_from_paper.json"
        
        with open(example_path) as f:
            procedure = json.load(f)
        
        # Validate
        validator = ProcedureValidator()
        errors = validator.validate(procedure)
        
        # Should be valid
        assert errors == [], f"Example procedure has validation errors: {errors}"
        assert validator.is_valid(procedure)
    
    def test_invalid_procedure_missing_required(self):
        """Test that validation catches missing required fields."""
        invalid_procedure = {
            "schema_version": "procedure_ir_v0",
            # Missing "source" and "steps"
        }
        
        validator = ProcedureValidator()
        errors = validator.validate(invalid_procedure)
        
        assert len(errors) > 0
        assert not validator.is_valid(invalid_procedure)
    
    def test_invalid_procedure_wrong_schema_version(self):
        """Test that validation catches incorrect schema version."""
        invalid_procedure = {
            "schema_version": "wrong_version",
            "source": {
                "type": "methods_section",
                "text": "Some text"
            },
            "steps": []
        }
        
        validator = ProcedureValidator()
        errors = validator.validate(invalid_procedure)
        
        assert len(errors) > 0


class TestActionRequirements:
    """Test action requirements checking."""
    
    def test_fix_action_requirements(self):
        """Test requirements for fixation step."""
        required = ActionRequirements.get_required_params("fix")
        
        assert "fixative" in required
        assert "fixative_concentration" in required
        assert "duration_min" in required
        assert "temperature" in required
    
    def test_image_action_requirements(self):
        """Test requirements for imaging step."""
        required = ActionRequirements.get_required_params("image")
        
        assert "microscope_type" in required
        assert "objective_magnification" in required
        assert "objective_na" in required
        assert "channels" in required
    
    def test_check_missing_params_complete(self):
        """Test completeness check when all params present."""
        provided = ["fixative", "fixative_concentration", "duration_min", "temperature"]
        missing = ActionRequirements.check_missing_params("fix", provided)
        
        assert missing == []
    
    def test_check_missing_params_incomplete(self):
        """Test completeness check when params missing."""
        provided = ["fixative", "duration_min"]  # Missing concentration and temperature
        missing = ActionRequirements.check_missing_params("fix", provided)
        
        assert "fixative_concentration" in missing
        assert "temperature" in missing
    
    def test_completeness_score(self):
        """Test completeness scoring."""
        # All params present
        score_full = ActionRequirements.get_completeness_score(
            "fix",
            ["fixative", "fixative_concentration", "duration_min", "temperature"]
        )
        assert score_full == 1.0
        
        # Half params present
        score_half = ActionRequirements.get_completeness_score(
            "fix",
            ["fixative", "duration_min"]
        )
        assert score_half == 0.5
        
        # No params present
        score_zero = ActionRequirements.get_completeness_score("fix", [])
        assert score_zero == 0.0


class TestProcedureAnalysis:
    """Test procedure analysis functionality."""
    
    def test_analyze_example_procedure(self):
        """Test analysis of the example procedure."""
        # Load example
        example_path = Path(__file__).parent.parent / "examples" / "procedure_ir_from_paper.json"
        
        with open(example_path) as f:
            procedure = json.load(f)
        
        # Analyze each step
        total_steps = len(procedure["steps"])
        complete_steps = 0
        
        for step in procedure["steps"]:
            action = step["action"]
            params = [p["name"] for p in step.get("parameters", [])]
            missing = ActionRequirements.check_missing_params(action, params)
            
            if len(missing) == 0:
                complete_steps += 1
        
        # We expect some incomplete steps in the example
        assert total_steps > 0
        assert complete_steps < total_steps  # Some should be incomplete


@pytest.mark.asyncio
class TestPaperFetcher:
    """Test paper fetching (with mocked responses)."""
    
    async def test_normalize_doi_url(self):
        """Test DOI normalization."""
        from planlint.paper_fetcher import PaperFetcher
        
        # We can test URL normalization without API key
        fetcher = PaperFetcher.__new__(PaperFetcher)
        
        # DOI with prefix
        url1 = fetcher._normalize_url("10.1038/s41586-020-2649-2")
        assert url1 == "https://doi.org/10.1038/s41586-020-2649-2"
        
        # DOI with doi: prefix
        url2 = fetcher._normalize_url("doi:10.1038/nature12345")
        assert url2 == "https://doi.org/10.1038/nature12345"
        
        # PMID
        url3 = fetcher._normalize_url("PMID:33293615")
        assert url3 == "https://pubmed.ncbi.nlm.nih.gov/33293615/"
        
        # arXiv
        url4 = fetcher._normalize_url("arXiv:2012.12345")
        assert url4 == "https://arxiv.org/abs/2012.12345"
        
        # Already a URL
        url5 = fetcher._normalize_url("https://example.com/paper")
        assert url5 == "https://example.com/paper"


@pytest.mark.asyncio
class TestLLMExtractor:
    """Test LLM extraction (with mocked responses)."""
    
    def test_parse_valid_json_response(self):
        """Test parsing valid LLM JSON response."""
        from planlint.llm_extractor import LLMExtractor
        
        extractor = LLMExtractor.__new__(LLMExtractor)
        
        # Mock response with markdown
        response = """```json
{
  "schema_version": "procedure_ir_v0",
  "steps": [
    {
      "id": "step_1",
      "raw_text": "Test",
      "action": "fix",
      "parameters": []
    }
  ]
}
```"""
        
        result = extractor._parse_llm_response(response)
        
        assert result["schema_version"] == "procedure_ir_v0"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["action"] == "fix"
    
    def test_parse_invalid_json_response(self):
        """Test that invalid JSON raises error."""
        from planlint.llm_extractor import LLMExtractor
        
        extractor = LLMExtractor.__new__(LLMExtractor)
        
        with pytest.raises(ValueError, match="not valid JSON"):
            extractor._parse_llm_response("This is not JSON")
    
    def test_parse_json_missing_steps(self):
        """Test that JSON without steps raises error."""
        from planlint.llm_extractor import LLMExtractor
        
        extractor = LLMExtractor.__new__(LLMExtractor)
        
        response = '{"schema_version": "procedure_ir_v0"}'
        
        with pytest.raises(ValueError, match="missing 'steps'"):
            extractor._parse_llm_response(response)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
