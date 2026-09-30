# Local thesis applications

Run commands from this repository. All Python commands use `uv run`.
There is no scheduler, server, sync service or automatic form submitter.

## Continue in a new session

Say **continue** to resume research and application work, **apply to five** to
work toward five confirmed submissions, or **status** for an honest count.
An application attempt is not a submission. If all suitable roles are blocked,
report completed attempts and the exact missing facts; do not claim the target.

1. Read `candidate/facts.md`, `candidate/cv.json`, `data/session.md` if present,
   and `uv run src/tracker.py status`, `list`, and relevant `history ID`.
2. Inspect browser tabs before opening duplicates. Review blocked and interrupted
   attempts against saved observations before taking any action. Do not use a
   different person's logged-in applicant account.
3. Search official employer sources in `docs/SOURCES.md`, Finland first and then
   Europe. Confirm a thesis route, deadline, location, timing, required skills,
   enrollment restrictions and documents from each actual posting. Save the
   source and dated review privately. Search snippets alone cannot establish an
   opening. Record closed and unsuitable leads to avoid repeated work.
4. Import reviewed records. Queue scores are subjective ordering aids, not proof
   of eligibility. Reviews older than seven days are withheld until refreshed.
   A blank deadline means unknown, not indefinite availability.
5. Prepare or explicitly refresh a private packet. Tailor a letter using facts,
   record each exact form answer and its source, and inspect every final PDF.
   Proposed projects and unverified libraries must not become achievements.
6. Mark `in_progress` before submitting data to an employer. Complete suitable
   applications under the user's authorization. Stop for missing required facts,
   candidate authentication, CAPTCHAs, assessments or required original work.
   Move to another suitable role. Save the exact blocker and observed form state.
7. Before the final click, save the exact submitted document versions and answers.
   After an actual employer receipt, save screenshot/text with URL, observation
   time and confirmation wording. Only then mark submitted with evidence.
8. End by updating private `data/session.md`: confirmed submissions, attempts,
   blockers, active tabs and next actions. Keep receipts and original packets.

## Commands

```sh
uv sync
uv run pytest -q
uv run src/cv.py candidate/cv.json output/pdf/cv.pdf
uv run src/tracker.py add data/research/opportunities.json
uv run src/tracker.py queue
uv run src/tracker.py show 1
uv run src/tracker.py prepare 1
uv run src/tracker.py mark 1 in_progress --note 'Opened official application form'
uv run src/tracker.py mark 1 blocked --note 'Required transcript missing; resume after supplied'
uv run src/tracker.py history 1
uv run src/tracker.py status
```

Use `--db tmp/demo.db` before the subcommand for isolated experiments.
`examples/opportunity.json` is fictional and must never be imported into a live search.

`prepare` creates `applications/0001/`: description, dated job snapshot, CV,
candidate snapshot, answer ledger and manifest. Existing packets are never
replaced. After source CV/facts change, `refresh ID --cv PATH --facts PATH`
creates a sibling revision and preserves blocked/interrupted status. Review and
copy still-valid tailored letters and answers explicitly; old packets stay intact.
Never use refresh to erase an uncertain submission. Check the employer portal
before resuming an interrupted final click. Use `mark ID in_progress --note ...`
only after that check. Submitted records cannot be reset.

```sh
uv run src/tracker.py mark 1 submitted \
  --note 'Observed employer receipt in browser; exact wording and URL saved' \
  --evidence applications/0001/receipt-observation.txt
```

The CLI checks evidence exists and saves its SHA-256; it cannot authenticate a
receipt or certify candidate eligibility. A fabricated receipt would defeat the
purpose. Core packet/source hashes detect changed CVs and candidate JSON. Save
all extra attachments and exact answers in the packet before submission. Recording
submission validates the ledger, saves submitted-answers.json and hashes every
packet artifact into the event. Do not edit submitted artifacts afterward.

## Private boundaries

`candidate/`, `data/`, `applications/`, `output/`, `tmp/`, `Resume.pdf`, environment
files and credentials are ignored. Local does not mean encrypted: normal OS file
permissions apply. Keep credentials in the browser/password manager, never Git.
Commit only tooling, fictional examples and general documentation. Inspect
`git diff --cached --name-only` and `git diff --cached` before every commit.
Use Conventional Commits and push immediately after every commit.
