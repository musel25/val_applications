from datetime import date
import json
import pytest
from tracker import Store


def role(**changes):
    item = dict(company='Example Lab', reference='MSC-1', title='MSc thesis: network anomaly detection', country='Finland', url='https://example.org/jobs?id=1', description='Six-month MSc thesis on network anomaly detection and machine learning.', deadline='2027-01-01', fit=85, reasons='Relevant ML research; confirm start date', thesis=True, reviewed_at='2026-09-29')
    item.update(changes)
    return item


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / 'jobs.db')


def test_reimport_deduplicates_and_preserves_blocker(store):
    first = store.add(role())
    store.mark(first, 'blocked', 'Candidate phone required')
    assert store.add(role(url='https://example.org/jobs?id=1&utm_source=mail')) == first
    assert store.get(first)['status'] == 'blocked'
    assert store.get(first)['note'] == 'Candidate phone required'
    assert len(store.list()) == 1


def test_reference_dedup_and_identity_queries(store):
    first = store.add(role())
    assert store.add(role(url='https://example.org/alternate')) == first
    assert store.add(role(reference='MSC-2', url='https://example.org/jobs?id=2')) != first


def test_queue_filters_deadline_thesis_geography_and_preserves_unknowns(store):
    good = store.add(role())
    for i, change in enumerate([dict(deadline='2026-09-28'), dict(thesis=False), dict(country='United States'), dict(country='Unknown')], 2):
        store.add(role(reference=f'MSC-{i}', url=f'https://example.org/{i}', **change))
    assert [r['id'] for r in store.queue(date(2026, 9, 29))] == [good]
    assert len(store.list()) == 5


def test_country_and_fit_validation(store):
    with pytest.raises(ValueError):
        store.add(role(fit=101))
    with pytest.raises(ValueError):
        store.add(role(deadline='tomorrow'))
    with pytest.raises(ValueError):
        store.add(role(url='file:///tmp/file'))


def test_finland_prioritized_before_other_europe(store):
    sweden = store.add(role(reference='S', url='https://example.org/sw', country='Sweden', fit=99))
    finland = store.add(role(fit=70))
    assert [r['id'] for r in store.queue(date(2026, 9, 29))] == [finland, sweden]


def test_prepare_preserves_existing_packet_and_rejects_submitted(store, tmp_path):
    job = store.add(role())
    cv = tmp_path / 'cv.pdf'
    cv.write_bytes(b'fixture pdf')
    facts = tmp_path / 'facts.json'
    facts.write_text('{"name":"Example"}')
    packet = store.prepare(job, tmp_path / 'applications', cv, facts, today=date(2026, 9, 29))
    (packet / 'notes.md').write_text('keep my notes')
    with pytest.raises(ValueError):
        store.prepare(job, tmp_path / 'applications', cv, facts, today=date(2026, 9, 29))
    assert (packet / 'notes.md').read_text() == 'keep my notes'
    assert store.get(job)['status'] == 'prepared'
    proof = packet / 'confirmation.txt'
    proof.write_text('Employer confirmation fixture')
    store.mark(job, 'submitted', 'Verified employer success', proof)
    with pytest.raises(ValueError):
        store.mark(job, 'discovered', 'reset')
    with pytest.raises(ValueError):
        store.prepare(job, tmp_path / 'applications', cv, facts)


def test_submission_requires_preparation_and_nonempty_evidence(store, tmp_path):
    job = store.add(role())
    with pytest.raises(ValueError):
        store.mark(job, 'submitted', 'No evidence')
    empty = tmp_path / 'empty.txt'
    empty.write_text('')
    with pytest.raises(ValueError):
        store.mark(job, 'submitted', 'Empty evidence', empty)
    assert store.get(job)['status'] == 'discovered'


def test_modified_cv_cannot_be_marked_submitted(store, tmp_path):
    job = store.add(role())
    cv = tmp_path / 'cv.pdf'
    cv.write_bytes(b'original pdf')
    facts = tmp_path / 'facts.json'
    facts.write_text('{}')
    packet = store.prepare(job, tmp_path / 'applications', cv, facts, today=date(2026, 9, 29))
    (packet / 'cv.pdf').write_bytes(b'changed')
    proof = packet / 'proof.txt'
    proof.write_text('confirmation')
    with pytest.raises(ValueError, match='changed'):
        store.mark(job, 'submitted', 'Verified', proof)
    assert store.get(job)['status'] == 'prepared'


def test_expired_role_cannot_be_prepared(store, tmp_path):
    job = store.add(role(deadline='2026-09-28'))
    with pytest.raises(ValueError):
        store.prepare(job, tmp_path / 'apps', tmp_path / 'cv', tmp_path / 'facts', today=date(2026, 9, 29))


def test_confirmation_hash_and_history_are_saved(store, tmp_path):
    job = store.add(role())
    cv = tmp_path / 'cv.pdf'; cv.write_bytes(b'pdf')
    facts = tmp_path / 'facts.json'; facts.write_text('{}')
    packet = store.prepare(job, tmp_path / 'apps', cv, facts, today=date(2026, 9, 29))
    proof = tmp_path / 'proof.txt'; proof.write_text('Application received')
    store.mark(job, 'submitted', 'Employer displayed receipt', proof)
    events = store.history(job)
    assert [e['status'] for e in events] == ['discovered', 'prepared', 'submitted']
    assert len(json.loads(events[-1]['evidence'])['sha256']) == 64
    assert (packet / 'confirmation.txt').read_text() == 'Application received'


def test_interrupted_attempt_survives_refresh_and_stays_out_of_queue(store, tmp_path):
    job = store.add(role(reviewed_at='2026-09-29'))
    cv = tmp_path / 'cv'; cv.write_bytes(b'cv')
    facts = tmp_path / 'facts'; facts.write_text('{}')
    old = store.prepare(job, tmp_path / 'apps', cv, facts, today=date(2026, 9, 29))
    store.mark(job, 'interrupted', 'Browser disconnected')
    cv.write_bytes(b'new cv')
    new = store.refresh(job, cv, facts, today=date(2026, 9, 29))
    assert new != old
    assert (old / 'cv.pdf').read_bytes() == b'cv'
    assert (new / 'cv.pdf').read_bytes() == b'new cv'
    assert store.get(job)['status'] == 'interrupted'
    assert store.queue(date(2026, 9, 29)) == []


def test_stale_review_and_changed_candidate_require_refresh(store, tmp_path):
    job = store.add(role(reviewed_at='2026-09-01'))
    assert store.queue(date(2026, 9, 29)) == []
    store.add(role(reviewed_at='2026-09-29'))
    cv = tmp_path / 'cv'; cv.write_bytes(b'cv')
    facts = tmp_path / 'facts'; facts.write_text('{}')
    store.prepare(job, tmp_path / 'apps', cv, facts, today=date(2026, 9, 29))
    facts.write_text('{"new":true}')
    proof = tmp_path / 'proof'; proof.write_text('receipt')
    with pytest.raises(ValueError, match='changed'):
        store.mark(job, 'submitted', 'Observed', proof)


def test_cli_persists_across_processes(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    cli = Path(__file__).resolve().parents[1] / 'src' / 'tracker.py'
    data = tmp_path / 'role.json'; data.write_text(json.dumps(role()))
    command = [sys.executable, str(cli), '--db', str(tmp_path / 'db')]
    added = subprocess.run(command + ['add', str(data)], capture_output=True, text=True, check=True)
    assert json.loads(added.stdout) == [1]
    subprocess.run(command + ['mark', '1', 'blocked', '--note', 'Phone required'], check=True, capture_output=True)
    listed = subprocess.run(command + ['list'], capture_output=True, text=True, check=True)
    assert json.loads(listed.stdout)[0]['note'] == 'Phone required'


def test_enriched_reference_and_old_url_both_deduplicate(store):
    job = store.add(role(reference=''))
    store.mark(job, 'blocked', 'Keep state')
    assert store.add(role(reference='A')) == job
    assert store.add(role(reference='A', url='https://example.org/new')) == job
    assert store.add(role(reference='', url='https://example.org/jobs?id=1')) == job
    assert len(store.list()) == 1
    assert store.get(job)['status'] == 'blocked'


@pytest.mark.parametrize('change,state', [
    ({'deadline':'2026-09-28'}, 'prepared'),
    ({'reviewed_at':'2026-09-01'}, 'prepared'),
    ({'country':'United States'}, 'prepared'),
    ({'thesis':False}, 'prepared'),
    ({}, 'closed'), ({}, 'excluded')])
def test_cannot_enter_application_after_scope_or_status_changes(store, tmp_path, change, state):
    job = store.add(role())
    cv = tmp_path / 'cv'; cv.write_bytes(b'cv')
    facts = tmp_path / 'facts'; facts.write_text('{}')
    store.prepare(job, tmp_path / 'apps', cv, facts, today=date(2026, 9, 29))
    store.add(role(**change))
    if state != 'prepared':
        store.mark(job, state, 'Not available')
    with pytest.raises(ValueError):
        store.mark(job, 'in_progress', 'Resume', today=date(2026, 9, 29))


def test_submission_requires_ledger_and_snapshots_all_artifacts(store, tmp_path):
    job = store.add(role())
    cv = tmp_path / 'cv'; cv.write_bytes(b'cv')
    facts = tmp_path / 'facts'; facts.write_text('{}')
    packet = store.prepare(job, tmp_path / 'apps', cv, facts, today=date(2026, 9, 29))
    (packet / 'answers.json').unlink()
    proof = tmp_path / 'proof.txt'; proof.write_text('received')
    with pytest.raises(ValueError, match='ledger'):
        store.mark(job, 'submitted', 'Observed', proof)
    answers = {'answers':[{'field':'Name', 'answer':'Example', 'provenance':'candidate.json', 'entered':True}], 'unknowns':[]}
    (packet / 'answers.json').write_text(json.dumps(answers))
    (packet / 'letter.txt').write_text('Tailored letter')
    store.mark(job, 'submitted', 'Observed', proof)
    evidence = json.loads(store.history(job)[-1]['evidence'])
    assert 'letter.txt' in evidence['artifacts']
    assert len(evidence['artifacts']['answers.json']) == 64
    assert json.loads((packet / 'submitted-answers.json').read_text()) == answers
    assert store.add(role()) == job
    assert store.get(job)['status'] == 'submitted'
