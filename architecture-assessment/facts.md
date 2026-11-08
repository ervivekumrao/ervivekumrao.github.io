# Architectural Facts & Raw Leads: ervivekumrao.github.io

## Codebase Metrics
- **Language Breakdown**: Python 3.12+, HTML5, CSS3, YAML (GitHub Workflows), Bash / PowerShell.
- **Python Source Lines of Code**: ~1,070 LOC across `tools/` and `tests/`.
  - `tools/build_site.py`: 430 lines
  - `tools/builder/renderers.py`: 412 lines
  - `tools/builder/styles.py`: 167 lines
  - `tools/builder/utils.py`: 45 lines
  - `tools/builder/github_api.py`: 37 lines
  - `tests/test_builder.py`: 156 lines
- **Dependencies (`requirements.txt`)**:
  - `markdown==3.7` (Markdown parsing)
  - `segno==1.6.1` (QR code SVG generation)
  - `pytest==8.3.4` (Test runner)

## Directory Structure & Modules
```
ervivekumrao.github.io/
├── .github/workflows/
│   ├── android-release.yml (136 lines) - Reusable workflow for building/signing/publishing Android app releases
│   └── site.yml (50 lines)             - GitHub Pages site build and deployment workflow
├── catalog/
│   ├── site.json (13 lines)             - Global site configuration metadata
│   └── projects/                        - 12 project metadata directories
│       ├── agenticinventory/
│       ├── appmanager/
│       ├── careercrox/
│       ├── childsafe/
│       ├── jitforge/
│       ├── medreminder/
│       ├── mockupmaster/
│       ├── officetimecounter/
│       ├── spindb/
│       ├── studycompanion/
│       ├── timespanselectorview/
│       └── tomcatvault/
├── scripts/
│   ├── set-app-secrets.ps1 (16 lines)   - PowerShell helper for uploading GitHub repository secrets
│   └── set-app-secrets.sh (16 lines)    - Bash helper for uploading GitHub repository secrets
├── static/
│   ├── favicon.svg (24 lines)
│   └── profile.jpg
├── tests/
│   └── test_builder.py (156 lines)      - Unit & integration tests
└── tools/
    ├── build_site.py (430 lines)        - Main CLI entrypoint
    ├── builder/                         - Package containing modules
    │   ├── __init__.py (2 lines)
    │   ├── github_api.py (37 lines)     - Release manifest fetching
    │   ├── renderers.py (412 lines)     - Component & project HTML renderers
    │   ├── styles.py (167 lines)        - CSS stylesheet definitions
    │   └── utils.py (45 lines)          - Escaping, sizing & title utilities
    └── fixtures/
        └── manifests.sample.json        - Offline test fixture
```

## Discovered Structural Facts & Observations
1. `tools/build_site.py` combines CLI argument parsing, catalog ingestion, index card assembly, and hardcoded HTML string constants for resume experience and skill competencies.
2. `tools/builder/styles.py` encapsulates raw CSS in a single multi-line string variable `CSS`.
3. `tools/builder/github_api.py` uses `urllib.request.urlopen` in a sequential `while True` loop over GitHub Releases API pages.
4. `tools/builder/renderers.py` uses `segno` for DPM QR code generation and inline SVG formatting.
5. Unit test coverage (`tests/test_builder.py`) tests utility functions and mock GitHub API calls, but does not test full `build_site.py` execution.
