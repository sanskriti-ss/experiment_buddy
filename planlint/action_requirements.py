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
        
        "treatment": ActionRequirement(
            action="treatment",
            required_params={
                "reagent",
                "concentration",
                "duration_min",
            },
            optional_params={
                "temperature",
                "volume",
                "solvent",
                "application_method"
            },
            description="General treatment or drug application"
        ),
        
        "seeding": ActionRequirement(
            action="seeding",
            required_params={
                "cell_line",
                "seeding_density",
                "medium",
            },
            optional_params={
                "volume",
                "plate_type",
                "coating",
                "passage_number",
                "culture_conditions"
            },
            description="Cell seeding and plating"
        ),
        
        "process": ActionRequirement(
            action="process",
            required_params={
                "method",
            },
            optional_params={
                "duration_min",
                "temperature",
                "equipment"
            },
            description="General processing step"
        ),
        
        "culturing": ActionRequirement(
            action="culturing",
            required_params={
                "medium",
                "duration_days",
            },
            optional_params={
                "temperature",
                "co2_percentage",
                "humidity",
                "feeding_schedule"
            },
            description="Cell or tissue culture maintenance"
        ),
        
        "formation": ActionRequirement(
            action="formation",
            required_params={
                "structure",
            },
            optional_params={
                "conditions",
                "duration_days",
                "growth_factors"
            },
            description="Formation of biological structures"
        ),
        
        "embed": ActionRequirement(
            action="embed",
            required_params={
                "embedding_medium",
            },
            optional_params={
                "temperature",
                "duration_min",
                "preparation_method"
            },
            description="Sample embedding for sectioning"
        ),
        
        "cost_analysis": ActionRequirement(
            action="cost_analysis",
            required_params={
                "method",
            },
            optional_params={
                "software",
                "parameters",
                "comparison_groups"
            },
            description="Cost-effectiveness analysis"
        ),
        
        "morphogenesis": ActionRequirement(
            action="morphogenesis",
            required_params={
                "developmental_stage",
            },
            optional_params={
                "growth_factors",
                "duration_days",
                "monitoring_method"
            },
            description="Morphological development process"
        ),
        
        "signaling": ActionRequirement(
            action="signaling",
            required_params={
                "pathway",
            },
            optional_params={
                "ligand",
                "concentration",
                "duration_min"
            },
            description="Cell signaling pathway analysis"
        ),
        
        "classification": ActionRequirement(
            action="classification",
            required_params={
                "criteria",
            },
            optional_params={
                "method",
                "software",
                "validation"
            },
            description="Classification or categorization step"
        ),
        
        "formulation": ActionRequirement(
            action="formulation",
            required_params={
                "components",
            },
            optional_params={
                "ratios",
                "mixing_method",
                "storage_conditions"
            },
            description="Formulation of solutions or compounds"
        ),
        
        "inhibition": ActionRequirement(
            action="inhibition",
            required_params={
                "inhibitor",
                "concentration",
            },
            optional_params={
                "duration_min",
                "target_pathway",
                "vehicle"
            },
            description="Inhibition of biological processes"
        ),
        
        "explanation": ActionRequirement(
            action="explanation",
            required_params={
                "topic",
            },
            optional_params={
                "method",
                "references",
                "context"
            },
            description="Explanatory or descriptive step"
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
    def get_completeness_score(cls, action: str, provided_params: List[str], raw_text: str = "") -> float:
        """
        Calculate completeness score (0-1) for a step.
        
        Args:
            action: Action type
            provided_params: List of parameter names that were found
            raw_text: Original text of the step (optional)
            
        Returns:
            Score from 0 (nothing specified) to 1 (all required params present)
        """
        # Check if this is non-procedural text
        if raw_text and cls.is_non_procedural_text(raw_text):
            return 0.1  # Very low score for background/descriptive text
            
        required = cls.get_required_params(action)
        if not required:
            # Unknown action type - check if text seems procedural
            if raw_text and cls.seems_procedural(raw_text):
                return 0.3  # Low score but not terrible for unknown procedural steps
            else:
                return 0.1  # Very low score for non-procedural unknown action
        
        provided_set = set(provided_params)
        found = len(required & provided_set)
        total = len(required)
        
        return found / total if total > 0 else 1.0
    
    @classmethod
    def is_non_procedural_text(cls, text: str) -> bool:
        """
        Detect if text is descriptive/background rather than procedural.
        
        Returns True for text that describes what something is or does,
        rather than instructions for what to do.
        """
        text_lower = text.lower().strip()
        
        # Patterns that indicate background/descriptive text
        descriptive_patterns = [
            # Present tense descriptions
            "are the", "is the", "are a", "is a",
            "play an important role", "play a role",
            "have been", "has been", 
            "are known to", "is known to",
            "are essential", "is essential",
            "are crucial", "is crucial",
            "are required", "is required",
            
            # Review language
            "studies have shown", "research has shown",
            "it has been demonstrated", "it has been shown",
            "previous studies", "recent studies",
            "in the literature", "as reviewed",
            
            # Definition/explanation patterns
            "which are", "that are", "this is",
            "these are", "such as", "for example",
            "in other words", "specifically",
            
            # Comparative/analytical language
            "in contrast", "however", "moreover",
            "furthermore", "additionally", "therefore",
            "consequently", "as a result",
            
            # Abstract concepts
            "the concept", "the idea", "the notion",
            "the principle", "the mechanism",
            
            # Passive descriptions of what exists
            "can be found", "are present", "are located",
            "are observed", "are seen", "exist",
        ]
        
        # Check if text contains multiple descriptive patterns
        matches = sum(1 for pattern in descriptive_patterns if pattern in text_lower)
        
        # Also check for lack of procedural language
        procedural_indicators = [
            # Action verbs in imperative or past tense
            "add", "remove", "wash", "incubate", "mix",
            "centrifuge", "pipet", "transfer", "dilute",
            "culture", "plate", "seed", "treat",
            "fix", "stain", "mount", "image",
            "were added", "was added", "were mixed",
            "were incubated", "was incubated",
            "were washed", "was washed",
        ]
        
        has_procedural = any(indicator in text_lower for indicator in procedural_indicators)
        
        return matches >= 2 and not has_procedural
    
    @classmethod  
    def seems_procedural(cls, text: str) -> bool:
        """
        Check if text seems like it describes a procedural step,
        even if we don't recognize the specific action.
        """
        text_lower = text.lower().strip()
        
        procedural_indicators = [
            # Direct action verbs
            "add", "remove", "wash", "incubate", "mix",
            "centrifuge", "pipet", "transfer", "dilute",
            "culture", "plate", "seed", "treat",
            "fix", "stain", "mount", "image", "prepare",
            "collect", "harvest", "extract", "purify",
            
            # Past tense experimental actions
            "were added", "was added", "were mixed", "was mixed",
            "were incubated", "was incubated", "were treated", "was treated",
            "were washed", "was washed", "were centrifuged", "was centrifuged",
            "were cultured", "was cultured", "were prepared", "was prepared",
            
            # Experimental parameters
            "for ", " min", " hour", " day", "°c", "rpm",
            "ml", "μl", "μg", "mg", "ng", "mm", "μm",
            "concentration", "volume", "temperature", "speed",
            
            # Procedural time/sequence words
            "then", "next", "subsequently", "after", "before",
            "following", "prior to", "until", "step",
        ]
        
        return any(indicator in text_lower for indicator in procedural_indicators)
    
    @classmethod
    def get_all_actions(cls) -> List[str]:
        """Get list of all supported action types."""
        return sorted(cls.REQUIREMENTS.keys())
    
    @classmethod
    def get_action_description(cls, action: str) -> str:
        """Get human-readable description of an action type."""
        req = cls.REQUIREMENTS.get(action)
        return req.description if req else "Unknown action type"
