# Experiment Buddy

A chrome extension prototype: just run it on any research paper that you're interested in replicating (in order to get a quick look for what is missing from the protocol that would be good to specify), or any proposed protocol doc that you wrote (to get suggestions on what you can improve in your research protocol, or any confounders that you are missing).

## Features

### 1. Experiment Plan Validation
Validates structured experiment plans against JSON Schema, catching common experimental design issues:
- Missing controls (positive, negative, blanks)
- Hidden confounders and batch effects
- QC and calibration gaps
- Parallelization opportunities
- Metadata completeness issues

### 2. Paper Procedure Extraction & Analysis
Automatically extracts and analyzes experimental procedures from scientific papers:
- **Fetch papers** from DOI, PubMed, arXiv, or direct URLs
- **Extract Methods sections** using LLM + web search (Dedalus + Exa)
- **Structure procedures** into machine-readable format
- **Flag missing details** that prevent reproducibility
- **Generate reports** highlighting underspecified protocols

## 3. Architecture

The system is built with modularity in mind:

1. **Canonical Schema**: Platform-agnostic experiment plan model (JSON Schema)
2. **Lint Engine**: Pure functions that validate plans and produce findings
3. **Adapters**: Platform-specific integrations (Benchling, Google Docs, etc.)
4. **Renderers**: Output formatting for different contexts

## Current Status: Step 2 Complete 

## Schema Structure

The `experiment_plan_microscopy_v0.schema.json` defines:

### Core Sections
- **Study**: Objective, assay type, primary outcomes
- **Design**: Conditions, replicates, randomization, controls
- **Samples**: Sample type, preparation, fluorophores, plate layout
- **Acquisition**: Microscope setup, channels, z-stack, time-lapse, environment, QC plan
- **Processing Plan**: Analysis steps and software
- **Outputs**: Raw data format, storage, naming conventions

### Why These Fields Matter

The schema is designed around common failure modes in microscopy:

1. **Controls & QC**: Unstained samples, single-color controls, calibration beads - all explicitly tracked because they're often forgotten
2. **Batch Variables**: Date, operator, instrument_id, etc. - critical for detecting confounders later
3. **Acquisition Parameters**: Channel settings, z-step size, exposure times - affects data quality and Nyquist sampling
4. **OME Compatibility**: Aligned with Open Microscopy Environment standards for interoperability

## Installation

```bash
# Clone the repository
git clone https://github.com/sanskriti-ss/experiment_buddy.git
cd experiment_buddy

# Install dependencies
pip install -r requirements.txt

# Set up Dedalus API key for paper extraction (optional)
export DEDALUS_API_KEY="your_key_here"
# Or create a .env file with: DEDALUS_API_KEY=your_key_here
```

## Usage

### Extract Procedure from a Paper (NEW!)

```bash
# Extract from DOI
python -m planlint.cli extract-paper 10.1038/s41586-020-2649-2 --output procedure.json --report analysis.json

# Extract from PubMed
python -m planlint.cli extract-paper PMID:33293615 --output procedure.json

# Extract from arXiv
python -m planlint.cli extract-paper arxiv:2012.12345

# Analyze an already-extracted procedure
python -m planlint.cli analyze-procedure examples/procedure_ir_from_paper.json
```

**What it does:**
1. Fetches the paper from the web
2. Finds and extracts the Methods section
3. Uses LLM to structure the procedure into steps with parameters
4. Validates against the procedure IR schema
5. Analyzes each step for missing required parameters
6. Generates a detailed completeness report

**Example output:**
```
✓ Found Methods section: Materials and Methods
  Length: 2847 characters
  
✓ Extracted 12 steps

✓ Valid procedure IR

Procedure Analysis Summary
━━━━━━━━━━━━━━━━━━━━━━━━━
Total Steps: 12
Complete: 6
Incomplete: 6
Missing Parameters: 15
Completeness: 50%

⚠ Steps Needing Attention:

step_7 (stain)
  Text: Nuclei were counterstained with DAPI.
  Missing:
    • concentration_or_dilution
    • duration_min
    • temperature
```

### Validate an Experiment Plan

```bash
# Validate a plan using the default microscopy schema
python -m planlint.validate examples/heart_organoid_fluorescence_plan.json

# Validate using a custom schema
python -m planlint.validate my_plan.json --schema custom_schema.json

# Disable colored output
python -m planlint.validate my_plan.json --no-color
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=planlint --cov-report=term-missing

# Run specific test file
pytest tests/test_validator.py -v
```

### Use in Python Code

```python
from pathlib import Path
from planlint.validator import validate_plan

# Validate a plan file
result = validate_plan(Path("my_plan.json"))

if result.is_valid:
    print("✓ Plan is valid!")
else:
    print("✗ Validation failed:")
    for error in result.errors:
        print(f"  - {error}")
```

## Next Steps

### Step 3: Lint Rules
First set of microscopy-specific lints:
- Missing controls (background, single-color for multichannel)
- Z-step too large (Nyquist sampling violation)
- Missing QC artifacts for quantitative imaging
- Metadata completeness checks
- Time-lapse interval warnings

### Step 4: Adapter Layer
- Define Adapter interface
- Implement MockBenchlingAdapter
- Add Google Docs structured block extractor

### Step 5: Simple UI
- JSON editor with schema validation
- Findings panel
- One-click fix application

## Design Principles

1. **Platform Agnostic**: Core linting logic never touches platform-specific code
2. **Testable**: Every rule can be tested with pure JSON fixtures
3. **Extensible**: New lint packs (omics, flow cytometry, etc.) plug in easily
4. **Generalizable**: Same approach works for Benchling, SciNote, Google Docs, etc.
5. **Modular**: Paper extraction is completely separate from experiment plan validation
6. **LLM-Powered**: Uses modern LLMs for intelligent text extraction, but validates deterministically

## How Paper Extraction Works

### Architecture

```
Paper URL → PaperFetcher → Methods Text → LLMExtractor → Procedure IR → Validator → Analysis Report
              (Dedalus+Exa)                (LLM)          (JSON)        (Schema)     (Missing params)
```

### Key Design Decisions

1. **Two-stage extraction**: First fetch the paper, then extract structure. Keeps concerns separated and testable.

2. **Intermediate Representation (IR)**: The `procedure_ir_v0` schema is separate from experiment plan schemas. This lets you:
   - Extract from papers without assuming a specific experimental platform
   - Test extraction without full plan validation
   - Map extracted procedures to multiple target schemas later

3. **Action-based requirements**: Each action type (fix, stain, image, etc.) has defined required parameters based on reproducibility best practices.

4. **Deterministic validation**: Even though extraction uses LLM, the completeness checking is rule-based and testable.

### Using with Chrome Extension (Future)

The current implementation is a **standalone CLI tool**. For browser integration:

1. **Option A**: Build a simple Chrome extension that:
   - Captures current URL
   - Calls the CLI tool via a local Python server
   - Displays results in a popup

2. **Option B**: Create a FastAPI backend that wraps the extraction pipeline, then build extension as thin UI client

The core logic stays in Python where it's testable and maintainable.

## File Structure

```
experiment_buddy/
├── schemas/
│   ├── experiment_plan_microscopy_v0.schema.json
│   └── procedure_ir_v0.schema.json              # NEW: Procedure IR schema
├── examples/
│   ├── heart_organoid_fluorescence_plan.json
│   ├── invalid_plan_missing_replicates.json
│   ├── procedure_ir_from_paper.json             # NEW: Example extracted procedure
│   └── paper_analysis_report.json               # NEW: Example analysis report
├── planlint/
│   ├── __init__.py
│   ├── validator.py           # Core validation logic
│   ├── validate.py            # CLI entry point
│   ├── paper_fetcher.py       # NEW: Fetch papers with LLM + Exa
│   ├── llm_extractor.py       # NEW: Extract structured procedures
│   ├── procedure_validator.py # NEW: Validate procedure IR
│   ├── action_requirements.py # NEW: Define required params per action
│   └── cli.py                 # NEW: Main CLI tool
├── tests/
│   ├── __init__.py
│   ├── test_validator.py
│   └── test_paper_extraction.py  # NEW: Tests for paper extraction
├── requirements.txt
├── pyproject.toml
├── .env                       # Optional: DEDALUS_API_KEY
└── README.md
```

## References

The schema design is informed by:
- Open Microscopy Environment (OME) metadata standards
- QUAREP-LiMi microscopy quality initiatives
- Nyquist sampling principles for z-stack acquisition
- Community best practices for reproducible microscopy

## License

[To be determined]
