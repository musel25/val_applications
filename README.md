# European thesis internship search

A simple, local workflow for finding European master's thesis internships,
prioritizing Finland. Inspired by `job-search-2026`: verified candidate facts,
role-specific documents, duplicate prevention and evidence-backed application
records. No VPS or background services.

Python tooling uses `uv`. Candidate documents, contact details and application
records stay local and are excluded from this public repository.

## Structure

- `src/`: search and application tracker
- `tests/`: workflow checks
- `config/`: public search sources and scope
- `templates/`: reusable document templates
- `docs/`: operating instructions
- `candidate/`, `data/`, `applications/`, `output/`: private local material
