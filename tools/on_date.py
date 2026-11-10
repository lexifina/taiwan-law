"""Print a Taiwanese law, or one article of it, as this repository has it on a date.

    python tools/on_date.py 2026-10-01 criminal-code              # the whole law, in the page's order
    python tools/on_date.py 2026-10-01 criminal-code 185-3        # one article (第 185-3 條)
    python tools/on_date.py 2026-10-01 criminal-code/article/1.md # one file
    python tools/on_date.py 2026-10-01 law/1935/C0000001 185-3      # the same, by its folder

A law's folder is <kind>/<year>/<code> (data/paths.json maps each earlier folder name, such as criminal-code or
reg-d0050166, to it); either name works, and versions recorded under the earlier name are read too.

Reads the `In-force:` trailer (commit dates before 1970 are clamped). Some laws have every version from
立法院法律系統 (lis.ly.gov.tw); the others have one version, dated by the date the law.moj.gov.tw page states.
Standard library only.
"""
import json
import re
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', check=True).stdout


def folders() -> dict:
    """{earlier folder name: folder} from data/paths.json on main ({} before the layout move)."""
    try:
        return json.loads(git('show', 'main:data/paths.json')).get('paths', {})
    except (subprocess.CalledProcessError, ValueError):
        return {}


def resolve(target: str, paths: dict) -> tuple[str, str, str]:
    """(path, law folder, earlier path) for a target named by its folder or by its earlier name."""
    parts = target.split('/')
    for i in range(len(parts), 0, -1):
        head, rest = '/'.join(parts[:i]), '/'.join(parts[i:])
        if head in paths:
            new = paths[head]
            return '/'.join(x for x in (new, rest) if x), new, target
    back = {v: k for k, v in paths.items()}
    for i in range(len(parts), 0, -1):
        head, rest = '/'.join(parts[:i]), '/'.join(parts[i:])
        if head in back:
            return target, head, '/'.join(x for x in (back[head], rest) if x)
    return target, parts[0], target


def commit_on(day: str, path: str, old: str = ''):
    fmt = '%H%x1f%(trailers:key=In-force,valueonly,separator=)'
    earliest = None
    for line in git('log', '--no-merges', f'--format={fmt}', 'main', '--', *dict.fromkeys([path, old or path])).splitlines():
        h, d = (line.split('\x1f') + [''])[:2]
        d = d.strip()
        if not d:
            continue
        earliest = d
        if d <= day:
            return h, d
    return None, earliest


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3 or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', sys.argv[1]):
        sys.exit(__doc__)
    day, target = sys.argv[1], sys.argv[2].strip('/')
    if len(sys.argv) > 3:
        target = f'{target}/article/{sys.argv[3].removesuffix(".md")}.md'
    target, law, old = resolve(target, folders())
    h, earliest = commit_on(day, target, old)
    if not h:
        if earliest:
            sys.exit(f'{target}: no version on or before {day}; the record starts at {earliest} '
                     '(law.moj.gov.tw is used for current text only)')
        sys.exit(f'{target}: not found')
    # a version from before the layout move has the law under its earlier folder name
    if subprocess.run(['git', 'cat-file', '-e', f'{h}:{target}'], capture_output=True).returncode:
        target, law = old, old.split('/article/')[0].removesuffix('/structure.md') if old != target else law
        if not target.endswith('.md'):
            law = target
    if target.endswith('.md'):
        sys.stdout.write(git('show', f'{h}:{target}'))
        return
    lines = git('show', f'{h}:{law}/structure.md').splitlines()
    specs = [f'{h}:{law}/{m.group(2)}' for m in (re.match(r'- (.+?): (\S+\.md)', x) for x in lines) if m]
    # one `git cat-file --batch` for every file of the law
    raw = subprocess.run(['git', 'cat-file', '--batch'], input=('\n'.join(specs) + '\n').encode('utf-8'),
                         capture_output=True, check=True).stdout
    blobs, pos = {}, 0
    for spec in specs:
        end = raw.index(b'\n', pos)
        size = int(raw[pos:end].split()[2])
        blobs[spec] = raw[end + 1:end + 1 + size].decode('utf-8')
        pos = end + 1 + size + 1
    for line in lines:
        m = re.match(r'- (.+?): (\S+\.md)', line)
        if m:
            label = '' if m.group(1) == '前言' else m.group(1) + '\n'
            sys.stdout.write(label + blobs[f'{h}:{law}/{m.group(2)}'])
        else:
            sys.stdout.write(line.lstrip('# ') + '\n')


if __name__ == '__main__':
    main()
