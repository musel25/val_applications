"""Private local opportunity tracker. A human must verify employer confirmation."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

EUROPE = {x.replace('_', ' ') for x in 'Albania Andorra Austria Belarus Belgium Bosnia_and_Herzegovina Bulgaria Croatia Cyprus Czechia Czech_Republic Denmark Estonia Finland France Germany Greece Hungary Iceland Ireland Italy Kosovo Latvia Liechtenstein Lithuania Luxembourg Malta Moldova Monaco Montenegro Netherlands North_Macedonia Norway Poland Portugal Romania San_Marino Serbia Slovakia Slovenia Spain Sweden Switzerland Türkiye Turkey Ukraine United_Kingdom Vatican_City'.split()}
STATES = {'discovered', 'prepared', 'in_progress', 'interrupted', 'blocked', 'submitted', 'closed', 'excluded'}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_url(url):
    parts = urlsplit(url.strip())
    if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
        raise ValueError('An HTTP(S) employer URL without credentials is required')
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in {'gclid', 'fbclid'}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/') or '/', urlencode(sorted(query)), ''))


class Store:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY, company TEXT NOT NULL, reference TEXT NOT NULL,
          url TEXT NOT NULL UNIQUE, payload TEXT NOT NULL, status TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '', packet TEXT, reviewed_at TEXT NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS employer_reference ON jobs(company, reference) WHERE reference != '';
        CREATE TABLE IF NOT EXISTS url_aliases (url TEXT PRIMARY KEY, job_id INTEGER NOT NULL);
        INSERT OR IGNORE INTO url_aliases(url,job_id) SELECT url,id FROM jobs;
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL, at TEXT NOT NULL,
          status TEXT NOT NULL, note TEXT NOT NULL, evidence TEXT NOT NULL DEFAULT '{}');
        ''')

    def _event(self, job, status, note, evidence=None):
        self.db.execute('INSERT INTO events(job_id,at,status,note,evidence) VALUES(?,?,?,?,?)',
                        (job, now(), status, note, json.dumps(evidence or {})))

    def add(self, item):
        item = dict(item)
        for key in ('company', 'title', 'country', 'description', 'reasons'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f'{key} is required')
        if type(item.get('fit')) not in (int, float) or not 0 <= item['fit'] <= 100:
            raise ValueError('fit must be between 0 and 100')
        if type(item.get('thesis')) is not bool:
            raise ValueError('thesis must be a boolean')
        if item.get('deadline'):
            date.fromisoformat(item['deadline'])
        reviewed = item.get('reviewed_at', date.today().isoformat())
        date.fromisoformat(reviewed)
        item['reviewed_at'] = reviewed
        url = canonical_url(item['url'])
        company = item['company'].strip().casefold()
        reference = str(item.get('reference', '')).strip().casefold()
        existing = self.db.execute('SELECT * FROM jobs WHERE id IN (SELECT job_id FROM url_aliases WHERE url=?) OR (company=? AND reference=? AND reference != ?)',
                                   (url, company, reference, '')).fetchall()
        if len(existing) > 1:
            raise ValueError('URL and employer reference identify different records; review duplicates manually')
        with self.db:
            if existing:
                row = existing[0]
                reference = reference or row['reference']
                item['reference'] = item.get('reference') or json.loads(row['payload']).get('reference', '')
                self.db.execute('UPDATE jobs SET company=?,reference=?,url=?,payload=?, reviewed_at=? WHERE id=?', (company, reference, url, json.dumps(item), reviewed, row['id']))
                self.db.execute('INSERT OR IGNORE INTO url_aliases(url,job_id) VALUES(?,?)', (url, row['id']))
                self._event(row['id'], row['status'], 'Official-source review refreshed; application state preserved', {'review': item})
                return row['id']
            cursor = self.db.execute('INSERT INTO jobs(company,reference,url,payload,status,reviewed_at) VALUES(?,?,?,?,?,?)',
                                     (company, reference, url, json.dumps(item), 'discovered', reviewed))
            self.db.execute('INSERT INTO url_aliases(url,job_id) VALUES(?,?)', (url, cursor.lastrowid))
            self._event(cursor.lastrowid, 'discovered', 'Opportunity recorded', {'review': item})
            return cursor.lastrowid

    def get(self, job):
        row = self.db.execute('SELECT * FROM jobs WHERE id=?', (job,)).fetchone()
        if row is None:
            raise ValueError(f'Unknown opportunity {job}')
        result = json.loads(row['payload'])
        result.update({k: row[k] for k in ('id', 'status', 'note', 'packet', 'reviewed_at')})
        return result

    def list(self):
        return [self.get(row[0]) for row in self.db.execute('SELECT id FROM jobs ORDER BY id')]

    def history(self, job):
        self.get(job)
        return [dict(r) for r in self.db.execute('SELECT * FROM events WHERE job_id=? ORDER BY id', (job,))]

    @staticmethod
    def eligible(item, today):
        return (item['thesis'] and item['country'] in EUROPE
                and (not item.get('deadline') or date.fromisoformat(item['deadline']) >= today)
                and 0 <= (today - date.fromisoformat(item['reviewed_at'])).days <= 7)

    def queue(self, today=None):
        today = today or date.today()
        return sorted((r for r in self.list() if r['status'] == 'discovered' and self.eligible(r, today)),
                      key=lambda r: (r['country'] != 'Finland', -r['fit'], r['id']))

    def prepare(self, job, root, cv, facts, today=None, *, revision=False):
        item = self.get(job)
        today = today or date.today()
        if (item['status'] in {'submitted', 'closed', 'excluded'} or not self.eligible(item, today)
                or (not revision and (item['packet'] or item['status'] not in {'discovered', 'blocked'}))):
            raise ValueError('Role is expired, stale, out of scope, already prepared or protected')
        cv, facts = Path(cv).resolve(), Path(facts).resolve()
        # Validate everything before creating a packet; never erase partial work.
        json.loads(facts.read_text())
        sources = {'cv.pdf': cv, 'candidate.json': facts}
        hashes = {name: digest(path) for name, path in sources.items()}
        suffix = ('-r' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')) if revision else ''
        packet = (Path(root) / (f'{job:04d}' + suffix)).resolve()
        packet.mkdir(parents=True, exist_ok=False)
        for name, path in sources.items():
            shutil.copyfile(path, packet / name)
        (packet / 'job.json').write_text(json.dumps(item, indent=2, ensure_ascii=False))
        (packet / 'description.txt').write_text(f"Source: {item['url']}\nReviewed: {item['reviewed_at']}\n\n{item['description']}\n")
        (packet / 'answers.json').write_text(json.dumps({'answers': [], 'unknowns': [], 'instructions': 'Save exact field, answer, provenance and whether actually entered. Never infer missing facts.'}, indent=2))
        hashes.update({name: digest(packet / name) for name in ('job.json', 'description.txt')})
        manifest = {'created_at': now(), 'files': hashes, 'sources': {name: {'path': str(path), 'sha256': hashes[name]} for name, path in sources.items()}}
        (packet / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        status = item['status'] if revision else 'prepared'
        note = item['note'] if revision else 'Private packet created'
        with self.db:
            self.db.execute('UPDATE jobs SET packet=?, status=?, note=? WHERE id=?', (str(packet), status, note, job))
            self._event(job, status, 'New packet revision created' if revision else note, manifest)
        return packet

    def refresh(self, job, cv, facts, today=None):
        item = self.get(job)
        if not item['packet']:
            raise ValueError('Prepare first')
        return self.prepare(job, Path(item['packet']).parent, cv, facts, today, revision=True)

    def mark(self, job, status, note, evidence=None, *, today=None):
        item = self.get(job)
        if status not in STATES or not note.strip():
            raise ValueError('A valid status and explanatory note are required')
        if item['status'] == 'submitted':
            raise ValueError('Submitted records cannot be reset; record follow-up outside status')
        if status in {'discovered', 'prepared'}:
            raise ValueError('Cannot reset protected state; refresh reviews or resume explicitly')
        if status == 'in_progress':
            if (not item['packet'] or item['status'] not in {'prepared', 'blocked', 'interrupted', 'in_progress'}
                    or not self.eligible(item, today or date.today())):
                raise ValueError('Cannot apply: role must be prepared, current, in scope and resumable')
        proof = {}
        if status == 'submitted':
            if not item['packet'] or not evidence or not Path(evidence).is_file() or not Path(evidence).stat().st_size:
                raise ValueError('Submission requires a prepared packet and nonempty employer evidence')
            packet = Path(item['packet'])
            try:
                answers = json.loads((packet / 'answers.json').read_text())
                if not isinstance(answers, dict) or not isinstance(answers.get('answers'), list):
                    raise ValueError('Invalid answer ledger')
                for entry in answers['answers']:
                    if (not isinstance(entry, dict) or not {'field', 'answer', 'provenance', 'entered'} <= entry.keys()
                            or not entry['provenance'] or type(entry['entered']) is not bool):
                        raise ValueError('Answer ledger entries need field, answer, provenance and entered flag')
            except (OSError, ValueError) as exc:
                raise ValueError('Valid answer ledger required before submission') from exc
            manifest = json.loads((packet / 'manifest.json').read_text())
            for name, expected in manifest['files'].items():
                if not (packet / name).is_file() or digest(packet / name) != expected:
                    raise ValueError(f'Packet changed: {name}')
            for name, source in manifest['sources'].items():
                if not Path(source['path']).is_file() or digest(source['path']) != source['sha256']:
                    raise ValueError(f'Candidate source changed: {name}; review and refresh packet')
            # Do not overwrite an existing receipt, even after an interrupted transaction.
            target = packet / ('confirmation' + (Path(evidence).suffix or '.txt'))
            raw = Path(evidence).read_bytes()
            if target.exists() and target.read_bytes() != raw:
                raise ValueError('A different confirmation already exists')
            target.write_bytes(raw)
            (packet / 'submitted-answers.json').write_text(json.dumps(answers, indent=2, ensure_ascii=False))
            artifacts = {str(p.relative_to(packet)): digest(p) for p in packet.rglob('*') if p.is_file()}
            proof = {'path': str(target), 'sha256': digest(target), 'observed_at': now(), 'artifacts': artifacts, 'answers': answers}
        with self.db:
            self.db.execute('UPDATE jobs SET status=?, note=? WHERE id=?', (status, note, job))
            self._event(job, status, note, proof)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=Path('data/jobs.db'))
    sub = parser.add_subparsers(dest='command', required=True)
    add = sub.add_parser('add'); add.add_argument('file', type=Path)
    for name in ('list', 'queue', 'status'):
        sub.add_parser(name)
    for name in ('show', 'history'):
        child = sub.add_parser(name); child.add_argument('id', type=int)
    prep = sub.add_parser('prepare'); prep.add_argument('id', type=int)
    prep.add_argument('--root', type=Path, default=Path('applications'))
    prep.add_argument('--cv', type=Path, default=Path('output/pdf/Valeria_Enriquez_Limon_CV.pdf'))
    prep.add_argument('--facts', type=Path, default=Path('candidate/cv.json'))
    refresh = sub.add_parser('refresh'); refresh.add_argument('id', type=int)
    refresh.add_argument('--cv', type=Path, default=Path('output/pdf/Valeria_Enriquez_Limon_CV.pdf'))
    refresh.add_argument('--facts', type=Path, default=Path('candidate/cv.json'))
    mark = sub.add_parser('mark'); mark.add_argument('id', type=int); mark.add_argument('status', choices=sorted(STATES))
    mark.add_argument('--note', required=True); mark.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    store = Store(args.db)
    try:
        if args.command == 'add':
            data = json.loads(args.file.read_text()); result = [store.add(r) for r in (data if isinstance(data, list) else [data])]
        elif args.command in {'list', 'queue'}:
            result = getattr(store, args.command)()
        elif args.command == 'status':
            result = {state: sum(r['status'] == state for r in store.list()) for state in sorted(STATES)}
        elif args.command in {'show', 'history'}:
            result = getattr(store, 'get' if args.command == 'show' else 'history')(args.id)
        elif args.command == 'prepare':
            result = str(store.prepare(args.id, args.root, args.cv, args.facts))
        elif args.command == 'refresh':
            result = str(store.refresh(args.id, args.cv, args.facts))
        else:
            store.mark(args.id, args.status, args.note, args.evidence); result = store.get(args.id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(2, f'Error: {exc}\n')
    finally:
        store.db.close()


if __name__ == '__main__':
    main()
