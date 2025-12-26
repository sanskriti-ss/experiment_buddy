"""
Define required parameters for each experimental action type.

This module specifies what information is minimally necessary for each
type of experimental step to be reproducible, enabling automated detection
of underspecified protocols.
"""

from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class ActionRequirement:
    """Required and optional parameters for an action type."""
    action: str
    required_params: Set[str]
    optional_params: Set[str]
    description: str


class ActionRequirements:
    """
    Registry of required parameters for experimental actions.
    
    Based on reproducibility guidelines from protocols.io, Bio-protocol,
    and JoVE best practices.
    """
    
    # Define requirements for each action type
    REQUIREMENTS: Dict[str, ActionRequirement] = {
        "fix": ActionRequirement(
            action="fix",
            required_params={
                "fixative",  # e.g., paraformaldehyde, methanol, glutaraldehyde
                "fixative_concentration",  # percentage or molarity
                "duration_min",
                "temperature",  # or "room temperature"
            },
            optional_params={
                "fixative_volume",
                "wash_buffer",
                "number_of_washes",
                "container_type"
            },
            description="Chemical fixation of biological samples"
        ),
        
        "permeabilize": ActionRequirement(
            action="permeabilize",
            required_params={
                "detergent",  # e.g., Triton X-100, Tween-20
                "detergent_concentration",  # percentage
                "duration_min",
            },
            optional_params={
                "temperature",
                "buffer_composition",
                "wash_steps"
            },
            description="Membrane permeabilization for antibody access"
        ),
        
        "block": ActionRequirement(
            action="block",
            required_params={
                "blocking_agent",  # e.g., BSA, serum, milk
                "concentration",  # percentage or mg/mL
                "duration_min",
            },
            optional_params={
                "temperature",
                "buffer",
                "additives"
            },
            description="Blocking non-specific binding sites"
        ),
        
        "stain": ActionRequirement(
            action="stain",
            required_params={
                "reagent_name",  # antibody, dye, etc.
                "concentration_or_dilution",  # e.g., 1:500, 2 ug/mL
                "duration_min",
                "temperature",
            },
            optional_params={
                "reagent_catalog_number",
                "reagent_vendor",
                "buffer",
                "wash_after",
                "light_protection"
            },
            description="Immunostaining or dye labeling"
        ),
        
        "wash": ActionRequirement(
            action="wash",
            required_params={
                "wash_buffer",  # e.g., PBS, PBST
                "number_of_washes",
                "duration_per_wash_min",
            },
            optional_params={
                "volume_per_wash",
                "agitation",
                "temperature"
            },
            description="Washing steps to remove excess reagents"
        ),
        
        "incubate": ActionRequirement(
            action="incubate",
            required_params={
                "duration_min",
                "temperature",
            },
            optional_params={
                "humidity",
                "co2_percent",
                "agitation",
                "light_conditions"
            },
            description="General incubation step"
        ),
        
        "mount": ActionRequirement(
            action="mount",
            required_params={
                "mounting_medium",  # e.g., ProLong, glycerol, VECTASHIELD
            },
            optional_params={
                "coverslip_thickness",
                "coverslip_size",
                "sealing_method",
                "curing_time"
            },
            description="Mounting samples for microscopy"
        ),
        
        "image": ActionRequirement(
            action="image",
            required_params={
                "microscope_type",  # confocal, widefield, light-sheet, etc.
                "objective_magnification",  # 10x, 20x, 40x, 63x, 100x
                "objective_na",  # numerical aperture
                "channels",  # wavelengths or fluorophores imaged
            },
            optional_params={
                "exposure_ms",
                "laser_power_percent",
                "detector_gain",
                "pixel_size_um",
                "z_step_um",
                "z_range_um",
                "time_interval",
                "frame_averaging",
                "pinhole_size",
                "immersion_medium",
                "binning"
            },
            description="Microscopy imaging parameters"
        ),
        
        "calibrate": ActionRequirement(
            action="calibrate",
            required_params={
                "calibration_type",  # spatial, intensity, spectral
                "calibration_standard",  # e.g., fluorescent beads, stage micrometer
            },
            optional_params={
                "calibration_date",
                "frequency"
            },
            description="Instrument calibration"
        ),
        
        "prepare_sample": ActionRequirement(
            action="prepare_sample",
            required_params={
                "sample_type",  # cells, tissue, organoid, etc.
                "preparation_method",
            },
            optional_params={
                "passage_number",
                "cell_density",
                "culture_medium",
                "substrate"
            },
            description="Sample preparation"
        ),
        
        "analyze": ActionRequirement(
            action="analyze",
            required_params={
                "software",
                "analysis_method",
            },
            optional_params={
                "software_version",
                "parameters",
                "thresholds"
            },
            description="Image or data analysis"
        ),
    }
    
    @classmethod
    def get_required_params(cls, action: str) -> Set[str]:
        """Get required parameters for an action type."""
        req = cls.REQUIREMENTS.get(action)
        if req:
            return req.required_params.copy()
        # For unknown actions, return empty set
        return set()
    
    @classmethod
    def get_optional_params(cls, action: str) -> Set[str]:
        """Get optional parameters for an action type."""
        req = cls.REQUIREMENTS.get(action)
        if req:
            return req.optional_params.copy()
        return set()
    
    @classmethod
    def check_missing_params(cls, action: str, provided_params: List[str]) -> List[str]:
        """
        Check which required parameters are missing.
        
        Args:
            action: Action type
            provided_params: List of parameter names that were found
            
        Returns:
            List of missing required parameter names
        """
        required = cls.get_required_params(action)
        provided_set = set(provided_params)
        
        missing = required - provided_set
        return sorted(missing)
    
    @classmethod
    def get_completeness_score(cls, action: str, provided_params: List[str]) -> float:
        """
        Calculate completeness score (0-1) for a step.
        
        Args:
            action: Action type
            provided_params: List of parameter names that were found
            
        Returns:
            Score from 0 (nothing specified) to 1 (all required params present)
        """
        required = cls.get_required_params(action)
        if not required:
            # Unknown action type, can't score
            return 0.5
        
        provided_set = set(provided_params)
        found = len(required & provided_set)
        total = len(required)
        
        return found / total if total > 0 else 1.0
    
    @classmethod
    def get_all_actions(cls) -> List[str]:
        """Get list of all supported action types."""
        return sorted(cls.REQUIREMENTS.keys())
    
    @classmethod
    def get_action_description(cls, action: str) -> str:
        """Get human-readable description of an action type."""
        req = cls.REQUIREMENTS.get(action)
        return req.description if req else "Unknown action type"
