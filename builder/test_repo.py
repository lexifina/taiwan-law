"""Functional smoke test of the built Taiwan law repository (current text only). Standard library only.

    python -X utf8 scripts/taiwan-law/test_repo.py [--repo C:/Users/alany/Documents/taiwan-law] [--record]
    python -X utf8 builder/test_repo.py                    # from inside the repository

Adapted from scripts/slovakia-law/test_repo.py. It asserts that:
1. `git blame` on an article names the law as author of every line;
2. tools/on_date.py gives the article on and after the law's page date (equal to the file), and refuses a day before;
3. every commit but the documentation commit has a well-formed `In-force:` trailer, in non-decreasing order, and
   every tag (if any) resolves;
4. no commit is authored by Lexifina except the documentation commit (the last one), and the committer is Lexifina;
5. every git or tool command in the README's question table runs and prints something;
6. every commit's trailers parse with `git interpret-trailers --parse` (ASCII keys).
With --record the result is merged into verification.json next to this script (for REPRODUCE.md).
"""
import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAW = re.compile(r'^\S.* \([A-Z]\d{7}\)$')


def default_repo() -> Path:
    if (HERE.parent / '.git').exists():
        return HERE.parent
    return HERE.parents[2] / 'taiwan-law'


class Smoke:
    def __init__(self, repo: Path):
        self.repo = repo
        self.results: list[tuple[str, bool, str]] = []

    def git(self, *args: str, inp: str | None = None) -> str:
        out = subprocess.run(['git', *args], cwd=self.repo, capture_output=True, text=True, encoding='utf-8', input=inp)
        if out.returncode:
            raise AssertionError(f'git {" ".join(args)}: {out.stderr.strip()}')
        return out.stdout

    def tool(self, *args: str, ok=True) -> str:
        out = subprocess.run([sys.executable, 'tools/on_date.py', *args], cwd=self.repo, capture_output=True, text=True,
                             encoding='utf-8')
        if ok and out.returncode:
            raise AssertionError(f'on_date {" ".join(args)}: {out.stderr.strip()}')
        if not ok:
            assert out.returncode, f'on_date {" ".join(args)} should have refused'
        return out.stdout

    def check(self, name: str, fn):
        try:
            detail = fn() or ''
            self.results.append((name, True, detail))
            print(f'PASS {name}: {detail}')
        except AssertionError as exc:
            self.results.append((name, False, str(exc)))
            print(f'FAIL {name}: {exc}')

    def blame(self):
        out = self.git('blame', '--line-porcelain', 'main', '--', 'criminal-code/article/271.md')
        authors = {l[7:] for l in out.splitlines() if l.startswith('author ')}
        assert authors == {'中華民國刑法 (C0000001)'}, f'unexpected authors {authors}'
        return f'criminal-code/article/271.md lines by {authors}'

    def on_date(self):
        done = []
        for law, art, day, before in [('criminal-code', '185-3', '2026-07-22', '2026-07-21'),
                                      ('constitution-additional-articles', '4', '2005-06-10', '2005-06-09'),
                                      ('constitution', '1', '1947-01-01', '1946-12-31')]:
            path = f'{law}/article/{art}.md'
            got = self.tool(day, law, art)
            assert got and got == self.git('show', f'main:{path}'), f'{path} on {day} is not the file'
            self.tool(before, law, art, ok=False)
            done.append(f'{path} from {day}')
        whole = self.tool('2026-10-28', 'constitution')
        assert '第 175 條' in whole and '中華民國基於三民主義' in whole, 'whole Constitution lacks art. 1 or 175'
        return '; '.join(done)

    def trailers(self):
        tags = self.git('tag').split()
        for t in tags:
            self.git('rev-parse', '--verify', '-q', f'{t}^{{commit}}')
        rows = self.git('log', '--reverse', '--format=%H%x09%an%x09%(trailers:key=In-force,valueonly,separator=)',
                        'main').splitlines()
        law = rows[:-1]
        days = [r.split('\t')[2].strip() for r in law]
        assert all(re.fullmatch(r'\d{4}-\d{2}-\d{2}', d) for d in days), f'malformed In-force {days}'
        assert days == sorted(days), f'In-force not in order {days}'
        return f'{len(law)} law commits carry In-force in order; {len(tags)} tags'

    def lexifina(self):
        rows = self.git('log', '--format=%H%x09%an%x09%ae%x09%cn', 'main').splitlines()
        by_lex = [r for r in rows if r.split('\t')[1] == 'Lexifina']
        assert len(by_lex) == 1 and by_lex[0] == rows[0], f'{len(by_lex)} commits by Lexifina'
        assert all(r.split('\t')[3] == 'Lexifina' for r in rows), 'a committer other than Lexifina'
        bad = [r for r in rows[1:] if not (LAW.match(r.split('\t')[1]) and r.split('\t')[2].endswith('.invalid'))]
        assert not bad, f'unexpected authors {bad}'
        return f'only the documentation commit is by Lexifina; {len(rows) - 1} law commits'

    def readme(self):
        text = (self.repo / 'README.md').read_text(encoding='utf-8')
        table = text[text.index('## Questions as git commands'):text.index('## Dates')]
        rows = '\n'.join(l for l in table.splitlines() if l.startswith('|'))
        cmds = [c for c in re.findall(r'`([^`]+)`', rows) if c.startswith(('git ', 'python ', 'cat '))]
        assert len(cmds) >= 5, f'only {len(cmds)} commands found'
        for c in cmds:
            args = shlex.split(c)
            if args[0] == 'python':
                args[0] = sys.executable
            if args[0] == 'cat':
                assert (self.repo / args[1]).read_text(encoding='utf-8').strip(), f'{c}: empty'
                continue
            out = subprocess.run(args, cwd=self.repo, capture_output=True, text=True, encoding='utf-8')
            assert out.returncode == 0, f'{c}: exit {out.returncode} {out.stderr.strip()[:200]}'
            assert out.stdout.strip(), f'{c}: printed nothing'
        return f'{len(cmds)} README commands ran and printed output'

    def parse_trailers(self):
        n = 0
        for h in self.git('rev-list', 'main').split():
            body = self.git('log', '-1', '--format=%B', h)
            if 'In-force:' in body:
                parsed = self.git('interpret-trailers', '--parse', inp=body)
                assert 'In-force:' in parsed, f'{h[:10]}: trailers do not parse'
                n += 1
        return f'{n} commits parse'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=None)
    ap.add_argument('--record', action='store_true')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    s = Smoke(Path(args.repo) if args.repo else default_repo())
    s.check('blame names the law', s.blame)
    s.check('on-date tool gives the text from the page date, nothing before', s.on_date)
    s.check('In-force on every law commit, in order; tags resolve', s.trailers)
    s.check('only the documentation commit is by Lexifina', s.lexifina)
    s.check('README commands run', s.readme)
    s.check('trailers parse', s.parse_trailers)
    ok = all(r[1] for r in s.results)
    print(f'{sum(r[1] for r in s.results)}/{len(s.results)} passed')
    if args.record:
        p = HERE / 'verification.json'
        rec = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rec['smoke'] = {'passed': sum(r[1] for r in s.results), 'total': len(s.results),
                        'results': [{'test': n, 'ok': o, 'detail': d} for n, o, d in s.results]}
        p.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
