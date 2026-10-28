"""Check lexifina/taiwan-law against the saved law.moj.gov.tw pages.

    python check_repo.py C:/Users/alany/Documents/taiwan-law [--ref main] [--write]

1. Byte check: every file of each law at its commit equals the parse of the saved page, and no other file exists
   in the law's folder.
2. Independent word-stream check: the letters and digits (casefolded) of EVERY text node inside the page's
   law-content block, read by a minimal tag-stripper that knows nothing of rows or articles, against the stream of
   the repo files (structure.md headings, article labels and article files, in structure.md order).
--write stores the result in verification.json (REPRODUCE.md quotes it).
"""
import gzip
import html
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402

WORD = re.compile(r'[^\W_]+')


def stream(text: str) -> str:
    return ''.join(WORD.findall(text)).casefold()


class Blobs:
    def __init__(self, repo):
        self.p = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get(self, spec: str) -> bytes | None:
        self.p.stdin.write(spec.encode('utf-8') + b'\n')
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if head[-1] == b'missing':
            return None
        n = int(head[2])
        b = self.p.stdout.read(n)
        self.p.stdout.read(1)
        return b


def raw_stream(page: str) -> str:
    """Independent extractor: the law-content block, all tags removed, the attachment banner dropped."""
    start = page.rindex('<', 0, page.index('id="pnLawFla"'))
    end = page.index('<!-- 主要內容結束 -->', start)
    block = page[start:end]
    block = block.replace('<span class="sr-only">本條文有附件</span>', '')
    return stream(html.unescape(re.sub(r'<[^>]*>', ' ', block)).replace('\u00ad', ''))


def repo_stream(blobs: Blobs, ref: str, folder: str) -> str:
    st = blobs.get(f'{ref}:{folder}/structure.md').decode('utf-8').split('\n')
    parts = []
    for line in st[3:]:
        m = re.match(r'- (.+?): (\S+\.md)', line)
        if m:
            if m.group(1) != '前言':
                parts.append(m.group(1))
            parts.append(blobs.get(f'{ref}:{folder}/{m.group(2)}').decode('utf-8'))
        elif line:
            parts.append(line.lstrip('#'))
    return stream(' '.join(parts))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    repo = sys.argv[1]
    ref = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else 'main'
    blobs = Blobs(repo)
    res = {'laws': {}, 'byte_mismatches': 0, 'stream_mismatches': 0}
    for pcode, folder, eng in build.ACTS:
        page = build.fetch(pcode, True)
        law = build.parse(page, pcode)
        want = build.render(law, folder)
        listed = subprocess.run(['git', 'ls-tree', '-r', '--name-only', ref, '--', folder + '/'], cwd=repo,
                                capture_output=True, text=True, encoding='utf-8', check=True).stdout.split()
        bad = sorted(set(listed) ^ set(want))
        for path in sorted(want):
            if blobs.get(f'{ref}:{path}') != want[path].encode('utf-8'):
                bad.append(path)
        rs, ps = repo_stream(blobs, ref, folder), raw_stream(page)
        ok = rs == ps
        if not ok:
            i = next((k for k in range(min(len(rs), len(ps))) if rs[k] != ps[k]), min(len(rs), len(ps)))
            print(f'{folder}: stream differs at {i}: repo {rs[max(0, i - 20):i + 30]!r} page {ps[max(0, i - 20):i + 30]!r}')
        res['laws'][folder] = {'files': len(want), 'byte_mismatches': len(bad), 'stream_chars': len(ps),
                               'stream_equal': ok}
        res['byte_mismatches'] += len(bad)
        res['stream_mismatches'] += 0 if ok else 1
        print(f'{folder}: {len(want)} files, {len(bad)} byte mismatches {bad[:5]}, stream {len(ps)} chars '
              f'{"equal" if ok else "DIFFERENT"}')
    print('RESULT', 'OK' if not (res['byte_mismatches'] or res['stream_mismatches']) else 'FAILED')
    if '--write' in sys.argv:
        vp = os.path.join(HERE, 'verification.json')
        rec = json.load(open(vp, encoding='utf-8')) if os.path.exists(vp) else {}
        rec['check_repo'] = res
        with open(vp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(rec, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write('\n')
    sys.exit(0 if not (res['byte_mismatches'] or res['stream_mismatches']) else 1)


if __name__ == '__main__':
    main()
