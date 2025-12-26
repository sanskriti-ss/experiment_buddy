"""
Unit tests for the validator module.

These tests ensure that:
1. Valid plans pass validation
2. Invalid plans fail with correct error messages
3. Edge cases are handled properly
4. Error formatting is clear and helpful
"""

import json
import pytest
from pathlib import Path
from planlint.validator import (
    load_schema,
    load_plan,
    validate_plan,
    validate_plan_dict,
    format_validation_error,
    ValidationResult
)
from jsonschema import ValidationError


# Get paths relative to this test file
TEST_DIR = Path(__file__).parent
REPO_ROOT = TEST_DIR.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
SCHEMAS_DIR = REPO_ROOT / "schemas"


class TestLoadSchema:
    """Tests for schema loading."""
    
    def test_load_default_schema(self):
        """Should load the default microscopy schema successfully."""
        schema = load_schema()
        
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "title" in schema
        assert schema["title"] == "ExperimentPlanMicroscopyV0"
    
    def test_load_custom_schema(self):
        """Should load a custom schema when path is provided."""
        schema_path = SCHEMAS_DIR / "experiment_plan_microscopy_v0.schema.json"
        schema = load_schema(schema_path)
        
        assert isinstance(schema, dict)
        assert schema["title"] == "ExperimentPlanMicroscopyV0"
    
    def test_load_nonexistent_schema(self):
        """Should raise FileNotFoundError for missing schema."""
        with pytest.raises(FileNotFoundError):
            load_schema(Path("nonexistent_schema.json"))


class TestLoadPlan:
    """Tests for plan loading."""
    
    def test_load_valid_plan(self):
        """Should load a valid plan file successfully."""
        plan_path = EXAMPLES_DIR / "heart_organoid_fluorescence_plan.json"
        plan = load_plan(plan_path)
        
        assert isinstance(plan, dict)
        assert "schema_version" in plan
        assert plan["schema_version"] == "microscopy_v0"
    
    def test_load_nonexistent_plan(self):
        """Should raise FileNotFoundError for missing plan."""
        with pytest.raises(FileNotFoundError):
            load_plan(Path("nonexistent_plan.json"))


class TestValidatePlan:
    """Tests for full plan validation."""
    
    def test_validate_valid_plan(self):
        """Should successfully validate a conforming plan."""
        plan_path = EXAMPLES_DIR / "heart_organoid_fluorescence_plan.json"
        result = validate_plan(plan_path)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.schema_version == "microscopy_v0"
        assert result.plan_path == str(plan_path)
    
    def test_validate_invalid_plan_missing_required(self):
        """Should catch missing required fields."""
        plan_path = EXAMPLES_DIR / "invalid_plan_missing_replicates.json"
        result = validate_plan(plan_path)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        
        # Should complain about missing replicates
        errors_text = " ".join(result.errors)
        assert "replicates" in errors_text.lower()
    
    def test_validate_invalid_plan_type_error(self):
        """Should catch type mismatches (negative exposure)."""
        plan_path = EXAMPLES_DIR / "invalid_plan_missing_replicates.json"
        result = validate_plan(plan_path)
        
        assert result.is_valid is False
        
        # Should complain about negative exposure_ms
        errors_text = " ".join(result.errors)
        assert "exposure_ms" in errors_text.lower() or "minimum" in errors_text.lower()
    
    def test_validate_nonexistent_plan(self):
        """Should handle missing plan files gracefully."""
        result = validate_plan(Path("nonexistent_plan.json"))
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()


class TestValidatePlanDict:
    """Tests for dictionary-based validation."""
    
    def test_validate_minimal_valid_plan(self):
        """Should validate a minimal but complete plan."""
        plan = {
            "schema_version": "microscopy_v0",
            "study": {
                "title": "Test Study",
                "objective": "Testing validation with minimal plan",
                "assay_type": "confocal_microscopy"
            },
            "design": {
                "conditions": [
                    {"id": "ctrl", "name": "Control"}
                ],
                "replicates": {
                    "biological_n": 3
                }
            },
            "samples": {
                "sample_type": "test cells",
                "preparation": {
                    "mounting": "standard"
                },
                "fluorophores": [
                    {"name": "GFP"}
                ]
            },
            "acquisition": {
                "microscope": {
                    "modality": "confocal",
                    "instrument_id": "scope_01",
                    "objective": {
                        "magnification_x": 20,
                        "numerical_aperture": 0.75
                    }
                },
                "channels": [
                    {
                        "name": "GFP",
                        "excitation_nm": 488,
                        "emission_nm": 510,
                        "exposure_ms": 50
                    }
                ]
            },
            "outputs": {
                "raw_data": {
                    "format": "ome_tiff",
                    "storage_location": "/data/test"
                },
                "naming": {
                    "pattern": "{date}_{condition}.tif"
                }
            }
        }
        
        is_valid, errors = validate_plan_dict(plan)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_invalid_schema_version(self):
        """Should catch invalid schema version enum."""
        plan = {
            "schema_version": "invalid_version",  # Wrong!
            "study": {
                "title": "Test",
                "objective": "Test objective",
                "assay_type": "confocal_microscopy"
            },
            "design": {
                "conditions": [{"id": "test", "name": "Test"}],
                "replicates": {"biological_n": 3}
            },
            "samples": {
                "sample_type": "test",
                "preparation": {"mounting": "test"},
                "fluorophores": [{"name": "GFP"}]
            },
            "acquisition": {
                "microscope": {
                    "modality": "confocal",
                    "instrument_id": "test",
                    "objective": {"magnification_x": 20, "numerical_aperture": 0.75}
                },
                "channels": [{
                    "name": "test",
                    "excitation_nm": 488,
                    "emission_nm": 510,
                    "exposure_ms": 50
                }]
            },
            "outputs": {
                "raw_data": {"format": "ome_tiff", "storage_location": "/test"},
                "naming": {"pattern": "test"}
            }
        }
        
        is_valid, errors = validate_plan_dict(plan)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "schema_version" in errors[0]
    
    def test_validate_missing_top_level_field(self):
        """Should catch missing required top-level sections."""
        plan = {
            "schema_version": "microscopy_v0",
            "study": {
                "title": "Test",
                "objective": "Test objective",
                "assay_type": "confocal_microscopy"
            }
            # Missing: design, samples, acquisition, outputs
        }
        
        is_valid, errors = validate_plan_dict(plan)
        
        assert is_valid is False
        assert len(errors) >= 4  # Should have at least 4 missing field errors


class TestErrorFormatting:
    """Tests for error message formatting."""
    
    def test_format_required_property_error(self):
        """Should format missing property errors clearly."""
        # Create a mock ValidationError for a missing property
        # This simulates what jsonschema produces
        plan = {"schema_version": "microscopy_v0"}
        schema = load_schema()
        
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(plan))
        
        # Should have errors about missing required fields
        assert len(errors) > 0
        
        from planlint.validator import format_validation_error
        formatted = [format_validation_error(e) for e in errors]
        
        # Check that errors are formatted with paths
        for error in formatted:
            assert ":" in error  # Should have "path: message" format


class TestValidationResult:
    """Tests for ValidationResult class."""
    
    def test_valid_result(self):
        """Should create a valid result correctly."""
        result = ValidationResult(
            is_valid=True,
            schema_version="microscopy_v0",
            plan_path="/path/to/plan.json"
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.schema_version == "microscopy_v0"
        assert "Valid" in repr(result)
    
    def test_invalid_result(self):
        """Should create an invalid result correctly."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            schema_version="microscopy_v0",
            plan_path="/path/to/plan.json"
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "Invalid" in repr(result)
        assert "2 errors" in repr(result)


# Run tests with: pytest tests/test_validator.py -v
