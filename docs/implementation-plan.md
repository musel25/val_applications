# Local thesis workflow implementation plan

**Goal:** a simple local search, CV and application workflow, with live test attempts.
**Spec:** [design.md](design.md)
**Stack:** Python 3.11+, uv, SQLite, ReportLab, pypdf, pytest; browser tools in-session.
**Execution:** inline, as authorized by the user's request to go ahead.

1. Build factual candidate JSON and a reusable CV renderer. Preserve input PDF;
   create `output/pdf/Valeria_Enriquez_Limon_CV.pdf`. Confirm one page, extracted
   content, clickable links and visual layout. Keep candidate files ignored.
2. Test and implement `Store.add`, `Store.prepare`, `Store.mark`, `Store.queue`:
   duplicate URLs/job references; scope and deadline checks; no re-preparation;
   no submitted status without evidence; stale documents require refresh; an
   interrupted attempt is never automatically resubmitted. SQLite is local.
3. Add a CLI for add/list/prepare/mark/status, a public source registry, generic
   candidate example, and instructions for natural-language continuation.
4. Research official European opportunities, prioritizing Finland. Save dated
   descriptions and fit explanations locally. Propose achievable portfolio
   projects with milestones and evaluation plans, clearly labeled future work.
5. Prepare tailored documents and attempt at least two relevant live forms.
   Save observed outcomes. Required unknown facts, candidate login and required
   original writing samples are explicit blockers, never invented answers.
6. Run the suite and a CLI smoke test, inspect the Git staged file list, and push
   each self-contained implementation commit. Report outputs and honest counts.

## Review focus

- Repeated imports cannot erase blocked/submitted state.
- A passed deadline must remove a role from the ready queue.
- A company board is a source, not a verified role.
- Job query parameters can carry identity and must not all be stripped.
- Raw HTML descriptions must be escaped in generated document output.

## Execution record

- Base repository created; initial setup committed and pushed.
- Source CV extracted; sibling architecture inspected; no sibling data copied.
