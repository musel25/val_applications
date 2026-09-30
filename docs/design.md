# Local thesis application workflow

## Brief

Support a master's student applying to thesis internships across Europe,
prioritizing Finland, in ML, data science, communications, security and autonomous
systems. The user authorized implementation and test applications in this session.
Use the existing sibling workflow as architectural inspiration, without its VPS,
sync services, US eligibility assumptions or original candidate data.

## Design

Use a small Python CLI with SQLite for durable state. The assistant discovers
roles from official employer pages, reads requirements, and records judgments;
keyword ranking is only a queue aid. Candidate JSON and document artifacts stay
local. A reusable ReportLab renderer produces editable-source, one-page CVs.
The browser performs real applications under the user's batch authorization.

Store source URL, dated requirements, country, deadline, fit reasons and unknowns.
Deduplicate by employer/job reference and canonical URL. Preserve every status
change in an event log. Preparation creates a private folder with the description,
CV, factual answer ledger and manifest. Never overwrite an existing packet.
Record employer confirmation and its hash before marking submitted. A stored
file cannot authenticate a submission: the assistant must actually observe it.
Never reset a submitted or interrupted attempt automatically.

Unknown availability, phone, permit status or transcripts remain unknown. New
project ideas never become CV achievements. Closed roles are not application
targets. Generic internships require a confirmed master's-thesis route.

No web server, scheduler, VPS, external API keys or broad ATS scraper is needed.
The checked-in repository contains only tooling, examples and operating guidance.

## Verification

Check duplicate imports, unknown geography, deadline filtering, non-thesis scope,
state transitions, packet freshness, preservation on repeated prep and confirmation
requirements using isolated SQLite databases. Render the CV and visually inspect
every page, text extraction and links. Test real employer forms after the CV is
ready and record exact blockers when completion requires missing candidate facts.
