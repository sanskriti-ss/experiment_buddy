"""
Validate procedure IR documents against the procedure_ir_v0 JSON schema.

This module provides validation for extracted procedures to ensure they
conform to the expected structure before further processing.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from jsonschema import validate, ValidationError, Draft202012Validator


class ProcedureValidator:
    """Validator for procedure IR documents."""
    
    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize validator with schema.
        
        Args:
            schema_path: Path to procedure_ir_v0.schema.json
                        If None, uses default location in schemas/
        """
        if schema_path is None:
            # Default: look in schemas/ directory relative to this file
            repo_root = Path(__file__).parent.parent
            schema_path = repo_root / "schemas" / "procedure_ir_v0.schema.json"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_path) as f:
            self.schema = json.load(f)
        
        self.validator = Draft202012Validator(self.schema)
    
    def validate(self, procedure: Dict[str, Any]) -> List[str]:
        """
        Validate a procedure IR document.
        
        Args:
            procedure: Procedure IR dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        for error in self.validator.iter_errors(procedure):
            # Format error message with path
            path = " -> ".join(str(p) for p in error.absolute_path)
            if path:
                msg = f"Error at {path}: {error.message}"
            else:
                msg = f"Error: {error.message}"
            errors.append(msg)
        
        return errors
    
    def validate_file(self, file_path: Path) -> List[str]:
        """
        Validate a procedure IR JSON file.
        
        Args:
            file_path: Path to JSON file to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        with open(file_path) as f:
            procedure = json.load(f)
        
        return self.validate(procedure)
    
    def is_valid(self, procedure: Dict[str, Any]) -> bool:
        """
        Check if a procedure IR document is valid.
        
        Args:
            procedure: Procedure IR dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        return len(self.validate(procedure)) == 0
    
    def validate_and_raise(self, procedure: Dict[str, Any]) -> None:
        """
        Validate and raise exception if invalid.
        
        Args:
            procedure: Procedure IR dictionary to validate
            
        Raises:
            ValidationError: If procedure is invalid
        """
        errors = self.validate(procedure)
        if errors:
            raise ValidationError(
                f"Procedure validation failed with {len(errors)} error(s):\n" +
                "\n".join(f"  - {e}" for e in errors)
            )
