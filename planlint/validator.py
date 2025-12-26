"""
Core validation module for experiment plans.

This module provides functions to validate experiment plan JSON files
against the canonical schema. It uses jsonschema for validation and
provides clear, structured error reporting.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from jsonschema import validate, ValidationError, SchemaError
from jsonschema.validators import Draft202012Validator


class ValidationResult:
    """
    Structured result from validating a plan.
    
    Attributes:
        is_valid: True if plan passes schema validation
        errors: List of validation error messages
        schema_version: The schema version that was validated against
        plan_path: Path to the plan file that was validated
    """
    
    def __init__(
        self, 
        is_valid: bool, 
        errors: List[str] = None,
        schema_version: str = None,
        plan_path: str = None
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.schema_version = schema_version
        self.plan_path = plan_path
    
    def __repr__(self):
        status = "Valid" if self.is_valid else "Invalid"
        return f"<ValidationResult {status}, {len(self.errors)} errors>"


def load_schema(schema_path: Optional[Path] = None) -> Dict:
    """
    Load a JSON schema from file.
    
    If no path is provided, loads the default microscopy_v0 schema
    from the schemas/ directory.
    
    Args:
        schema_path: Optional path to schema file. If None, uses default.
        
    Returns:
        Dict containing the parsed JSON schema
        
    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema file is not valid JSON
        SchemaError: If the loaded JSON is not a valid JSON Schema
    """
    if schema_path is None:
        # Default to the microscopy v0 schema in the schemas/ directory
        package_dir = Path(__file__).parent.parent
        schema_path = package_dir / "schemas" / "experiment_plan_microscopy_v0.schema.json"
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    # Validate that the schema itself is well-formed
    # This catches issues like malformed $ref, invalid keywords, etc.
    Draft202012Validator.check_schema(schema)
    
    return schema


def load_plan(plan_path: Path) -> Dict:
    """
    Load an experiment plan from a JSON file.
    
    Args:
        plan_path: Path to the plan JSON file
        
    Returns:
        Dict containing the parsed plan
        
    Raises:
        FileNotFoundError: If plan file doesn't exist
        json.JSONDecodeError: If plan file is not valid JSON
    """
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")
    
    with open(plan_path, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    
    return plan


def format_validation_error(error: ValidationError) -> str:
    """
    Format a jsonschema ValidationError into a human-readable message.
    
    JSON Schema errors can be complex. This function extracts the most
    relevant information and formats it clearly.
    
    Args:
        error: A ValidationError from jsonschema
        
    Returns:
        Formatted error string with JSON path and description
        
    Example output:
        "design.replicates.biological_n: 'biological_n' is a required property"
        "acquisition.channels[0].exposure_ms: -5 is less than the minimum of 0.01"
    """
    # Build the JSON path to the error (e.g., "design.replicates.biological_n")
    path_parts = []
    for part in error.absolute_path:
        if isinstance(part, int):
            # Array index
            path_parts[-1] = f"{path_parts[-1]}[{part}]"
        else:
            # Object property
            path_parts.append(str(part))
    
    json_path = ".".join(path_parts) if path_parts else "(root)"
    
    # Get the error message
    message = error.message
    
    # For required property errors, make it clearer
    if error.validator == "required":
        missing_property = error.message.split("'")[1]
        message = f"Missing required property '{missing_property}'"
    
    # For enum errors, show allowed values
    elif error.validator == "enum":
        allowed = error.validator_value
        message = f"Value not allowed. Must be one of: {allowed}"
    
    # For type errors, be specific
    elif error.validator == "type":
        expected = error.validator_value
        message = f"Wrong type. Expected {expected}"
    
    return f"{json_path}: {message}"


def validate_plan(
    plan_path: Path,
    schema_path: Optional[Path] = None
) -> ValidationResult:
    """
    Validate an experiment plan against a schema.
    
    This is the main validation function. It loads both the schema and plan,
    runs validation, and returns a structured result with any errors.
    
    Args:
        plan_path: Path to the experiment plan JSON file
        schema_path: Optional path to schema file. If None, uses default.
        
    Returns:
        ValidationResult object with validation status and errors
        
    Example:
        >>> result = validate_plan(Path("examples/my_plan.json"))
        >>> if result.is_valid:
        >>>     print("Plan is valid!")
        >>> else:
        >>>     for error in result.errors:
        >>>         print(f"  - {error}")
    """
    try:
        # Load schema and plan
        schema = load_schema(schema_path)
        plan = load_plan(plan_path)
        
        # Extract schema version from plan for reporting
        schema_version = plan.get("schema_version", "unknown")
        
        # Create a validator instance
        # This allows us to collect ALL errors, not just the first one
        validator = Draft202012Validator(schema)
        
        # Collect all validation errors
        errors = list(validator.iter_errors(plan))
        
        if errors:
            # Format each error into a readable message
            error_messages = [format_validation_error(err) for err in errors]
            return ValidationResult(
                is_valid=False,
                errors=error_messages,
                schema_version=schema_version,
                plan_path=str(plan_path)
            )
        else:
            # No errors - plan is valid!
            return ValidationResult(
                is_valid=True,
                schema_version=schema_version,
                plan_path=str(plan_path)
            )
    
    except FileNotFoundError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"File error: {str(e)}"],
            plan_path=str(plan_path)
        )
    
    except json.JSONDecodeError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"JSON parse error at line {e.lineno}, column {e.colno}: {e.msg}"],
            plan_path=str(plan_path)
        )
    
    except SchemaError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Schema error: {str(e)}"],
            plan_path=str(plan_path)
        )
    
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Unexpected error: {str(e)}"],
            plan_path=str(plan_path)
        )


def validate_plan_dict(
    plan: Dict,
    schema: Optional[Dict] = None
) -> Tuple[bool, List[str]]:
    """
    Validate a plan dictionary directly (without loading from file).
    
    This is useful for testing and for validating plans that are
    constructed programmatically.
    
    Args:
        plan: The experiment plan as a dictionary
        schema: Optional schema dictionary. If None, loads default.
        
    Returns:
        Tuple of (is_valid, error_messages)
        
    Example:
        >>> plan = {"schema_version": "microscopy_v0", ...}
        >>> is_valid, errors = validate_plan_dict(plan)
    """
    try:
        if schema is None:
            schema = load_schema()
        
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(plan))
        
        if errors:
            error_messages = [format_validation_error(err) for err in errors]
            return False, error_messages
        else:
            return True, []
    
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]
