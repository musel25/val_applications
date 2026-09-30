# Local master's thesis application workflow

A small Python CLI and SQLite tracker for European master's thesis internships,
with Finland-first prioritization, factual CV rendering and durable application
history. Candidate data, documents and application evidence stay local and out
of public Git history.

Start with [Operating instructions](docs/OPERATIONS.md). In an assistant session,
say **continue**, **apply to five**, or **status**. The assistant researches and
operates employer forms interactively; the CLI never submits applications.

```sh
uv sync
uv run pytest -q
uv run src/tracker.py status
uv run src/tracker.py queue
```

- [Architecture](docs/design.md)
- [Implementation plan](docs/implementation-plan.md)
- [Official discovery sources](docs/SOURCES.md)
- [Fictional opportunity example](examples/opportunity.json)

Private state: `data/jobs.db`, `data/session.md`, `candidate/`, `applications/`
and `output/`. There is no server, scheduled automation, VPS or sync layer.
