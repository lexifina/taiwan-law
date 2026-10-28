"""Build lexifina/taiwan-law: the current text of a few central laws of Taiwan (ROC) as a git history.

    python build.py --docs-date 2026-10-28 --out C:/Users/alany/Documents/taiwan-law [--offline]
    python build.py --docs-date 2026-10-28 --verify-rebuild        # build twice into temp dirs, compare hashes

Source: 全國法規資料庫 (law.moj.gov.tw), Ministry of Justice. robots.txt disallows everything except
/LawClass/LawAll.aspx (the current full text of one law), /News/NewsDetail.aspx and the sitemap, so the site's
past-version pages (LawHistory, LawOldVer) and its /api/ are NOT used. Each law therefore gets ONE commit: its text as
the page shows it, dated by the date the page states (修正日期 = last amendment, or 公布日期 = promulgation).

No model runs here. Standard library plus curl and git.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '.cache')
UA = 'LexifinaBot/1.0 (+https://lexifina.com; git-for-law; current text only, robots.txt obeyed)'
BASE = 'https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode='
COMMITTER = 'Lexifina <taiwan-law@lexifina.com>'
TZ = '+0800'  # Taiwan: UTC+8, no summer time since 1979 (all dates used here are 1980+ or clamped)

# (pcode, folder, English name). Order here is only a tie-break; commits go in date order.
ACTS = [
    ('A0000001', 'constitution', 'Constitution of the Republic of China (Taiwan)'),
    ('A0000002', 'constitution-additional-articles', 'Additional Articles of the Constitution of the Republic of China'),
    ('C0000001', 'criminal-code', 'Criminal Code of the Republic of China'),
    ('B0010001', 'code-of-civil-procedure', 'Code of Civil Procedure'),
    ('C0010001', 'code-of-criminal-procedure', 'Code of Criminal Procedure'),
]
# 民法 (B0000001) was fetched and left out: its page carries 生效狀態 "※本法規部分或全部條文尚未生效" (art. 1223 as
# amended 2026-08-17 takes effect six months after promulgation; art. 166-1 has no commencement date), so its text is
# not the text in force today, and the in-force text is only on LawOldVer.aspx, which robots.txt disallows.

ROC_DATE = re.compile(r'民國\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日')
ATTACH_NOTE = '本條文有附件'  # "this article has an attachment" (a PDF on the site, not text; not copied)
SOFT = re.compile('\u00ad')


def fetch(pcode: str, offline: bool) -> str:
    os.makedirs(CACHE, exist_ok=True)
    gi = os.path.join(CACHE, '.gitignore')
    if not os.path.exists(gi):
        with open(gi, 'w', newline='\n') as f:
            f.write('*\n')
    path = os.path.join(CACHE, pcode + '.html.gz')
    if not os.path.exists(path):
        if offline:
            sys.exit(f'--offline: {pcode} is not in the cache')
        r = subprocess.run(['curl', '-s', '--compressed', '-m', '90', '-A', UA, '-w', '%{http_code}', BASE + pcode],
                           capture_output=True, check=True)
        body, code = r.stdout[:-3], r.stdout[-3:]
        if code != b'200':
            sys.exit(f'{pcode}: HTTP {code!r}')
        with open(path, 'wb') as f:
            f.write(gzip.compress(body, mtime=0))
    return gzip.decompress(open(path, 'rb').read()).decode('utf-8')


def clean(s: str) -> str:
    return SOFT.sub('', html.unescape(s))


ROW = re.compile(
    r'<div class="h3 char-(\d)">([^<]*)</div>'
    r'|<div class="row"><div class="col-no">(.*?)</div><div class="col-data"><div class="law-article">(.*?)</div>\s*</div></div>',
    re.S)
ATTACH = '<i class="fa fa-paperclip" title="本條文有附件"></i><span class="sr-only">本條文有附件</span>'
LINE = re.compile(r'<div class="line-\d{4}(?: show-number)?">([^<]*)</div>')


def parse(page: str, pcode: str) -> dict:
    hdr = re.search(r'<div class="table-title">(.*?)<ul id="LawMenu"', page, re.S).group(1)
    name = clean(re.search(r'<a id="hlLawName"[^>]*>([^<]+)</a>', hdr).group(1)).strip()
    m = re.search(r'<th>(修正日期|公布日期)：</th>\s*<td>([^<]*)</td>', hdr)
    date_label, date_text = m.group(1), clean(m.group(2)).strip()
    y, mo, d = (int(x) for x in ROC_DATE.search(date_text).groups())
    cat = re.search(r'<th>法規類別：</th>\s*<td>([^<]*)</td>', hdr)
    status = 'VaildState' in hdr
    start = page.index('<div class="law-reg-content">') + len('<div class="law-reg-content">')
    end = page.index('\r\n\r\n                </div>', start)
    content = page[start:end]
    rows, pos, rest = [], 0, []
    for mm in ROW.finditer(content):
        rest.append(content[pos:mm.start()])
        pos = mm.end()
        if mm.group(1):
            rows.append(('heading', int(mm.group(1)), clean(mm.group(2)).strip()))
            continue
        no, inner = mm.group(3), mm.group(4)
        lines = [clean(x) for x in LINE.findall(inner)]
        left = LINE.sub('', inner)
        if lines:
            assert not left.strip(), (pcode, left[:200])
        else:
            assert '<' not in inner, (pcode, inner[:200])
            lines = [clean(inner).strip()]
        lines = [x.strip() for x in lines]
        assert all(lines), (pcode, no)
        att = no.startswith(ATTACH)
        if att:
            no = no[len(ATTACH):]
        a = re.fullmatch(r'\s*<a href="LawSingle\.aspx\?pcode=\w+&flno=([0-9]+(?:-[0-9]+)?)" name="\1">([^<]+)</a>', no)
        if a:
            rows.append(('article', a.group(1), clean(a.group(2)).strip(), lines, att))
        else:
            assert clean(no).strip() == '' and not att, (pcode, no)
            rows.append(('preamble', lines))
    rest.append(content[pos:])
    assert not ''.join(rest).strip(), (pcode, ''.join(rest).strip()[:300])
    arts = [r[1] for r in rows if r[0] == 'article']
    assert len(arts) == len(set(arts)), pcode
    return {'pcode': pcode, 'name': name, 'date_label': date_label, 'date_text': date_text,
            'date': f'{y + 1911:04d}-{mo:02d}-{d:02d}', 'category': clean(cat.group(1)).strip() if cat else '',
            'status_note': status, 'rows': rows}


def render(law: dict, folder: str) -> dict[str, str]:
    """Files of one law: {path: text}. Each article is one file, one paragraph (項/款 line) per line."""
    files = {}
    st = [law['name'], f"{law['date_label']}：{law['date_text']}", '']
    n_pre = 0
    for r in law['rows']:
        if r[0] == 'heading':
            st.append('#' * r[1] + ' ' + r[2])
        elif r[0] == 'preamble':
            n_pre += 1
            p = 'preamble.md' if n_pre == 1 else f'preamble-{n_pre}.md'
            files[f'{folder}/{p}'] = '\n'.join(r[1]) + '\n'
            st.append(f'- 前言: {p}')
        else:
            p = f'article/{r[1]}.md'
            files[f'{folder}/{p}'] = '\n'.join(r[3]) + '\n'
            st.append(f'- {r[2]}: {p}' + (f' ({ATTACH_NOTE})' if r[4] else ''))
    files[f'{folder}/structure.md'] = '\n'.join(st) + '\n'
    return files


def git_date(day: str) -> str:
    """Noon Taipei as a git raw date. Days before 1970 clamp to 1970-01-01 noon (real day kept in In-force)."""
    import datetime as dt
    y, m, d = (int(x) for x in day.split('-'))
    if y < 1970:
        y, m, d = 1970, 1, 1
    assert y >= 1980 or (y, m, d) == (1970, 1, 1), day  # no Taiwan summer time to model
    ts = int(dt.datetime(y, m, d, 4, 0, tzinfo=dt.timezone.utc).timestamp())  # 12:00 +0800 = 04:00 UTC
    return f'{ts} {TZ}'


def message(law: dict, folder: str, eng: str, retrieved: str) -> str:
    kind = 'amended' if law['date_label'] == '修正日期' else 'promulgated'
    subj = f"{law['name']}: current text, {kind} {law['date']}"
    body = (f"The text of {law['name']} ({eng}) as 全國法規資料庫 (law.moj.gov.tw) shows it, retrieved {retrieved}.\n"
            f"The page gives {law['date_label']} {law['date_text']}, so the commit is dated {law['date']}. That is the\n"
            f"promulgation day of the {'last amendment' if kind == 'amended' else 'law'}, not a commencement day the page states.\n"
            "The site's past versions are on pages robots.txt disallows, so this commit holds the whole text and\n"
            "nobody is credited with single lines.")
    if law['date'] < '1970-01-01':
        body += f"\nGit cannot store dates before 1970: the commit date is clamped to 1970-01-01; the real day is in In-force."
    tr = ['Kind: current-text', f"In-force: {law['date']}", f'In-force-basis: page-{kind}-date',
          f"Law: {law['name']}", f'Law-code: {law["pcode"]}', f'Law-en: {eng}',
          f'Source: {BASE}{law["pcode"]}', f'Retrieved: {retrieved}']
    return f'{subj}\n\n{body}\n\n' + '\n'.join(tr) + '\n'


class Writer:
    def __init__(self, repo: str):
        self.p = subprocess.Popen(['git', 'fast-import', '--quiet', '--done', '--force'], cwd=repo,
                                  stdin=subprocess.PIPE)
        self.mark = 0

    def w(self, b: bytes | str):
        self.p.stdin.write(b.encode('utf-8') if isinstance(b, str) else b)

    def data(self, s: str):
        b = s.encode('utf-8')
        self.w(f'data {len(b)}\n')
        self.w(b)
        self.w('\n')

    def commit(self, author: str, date: str, msg: str, files: dict[str, str], deleteall=False):
        self.mark += 1
        self.w(f'commit refs/heads/main\nmark :{self.mark}\nauthor {author} {date}\ncommitter {COMMITTER} {date}\n')
        self.data(msg)
        if self.mark > 1:
            self.w(f'from :{self.mark - 1}\n')
        for path in sorted(files):
            self.w(f'M 100644 inline {path}\n')
            self.data(files[path])

    def finish(self):
        self.w('done\n')
        self.p.stdin.close()
        if self.p.wait():
            sys.exit('git fast-import failed')


def blob_sha(path: str) -> str:
    b = open(path, 'rb').read()
    return hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()


def load(offline: bool):
    laws = []
    for pcode, folder, eng in ACTS:
        page = fetch(pcode, offline)
        law = parse(page, pcode)
        laws.append((law, folder, eng, hashlib.sha256(page.encode('utf-8')).hexdigest()))
    laws.sort(key=lambda x: (x[0]['date'], x[0]['pcode']))
    return laws


def build(out: str, docs_date: str, offline: bool) -> str:
    laws = load(offline)
    if os.path.isdir(os.path.join(out, '.git')):
        remote = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=out, capture_output=True, text=True).stdout.strip()
        for n in os.listdir(out):
            if n != '.git':
                p = os.path.join(out, n)
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    else:
        if os.path.isdir(out) and os.listdir(out):
            sys.exit(f'{out} is not empty and not a git repo: refusing')
        os.makedirs(out, exist_ok=True)
        subprocess.run(['git', 'init', '-q', '-b', 'main', out], check=True)
        remote = ''
    subprocess.run(['git', 'config', 'core.autocrlf', 'false'], cwd=out, check=True)
    subprocess.run(['git', 'symbolic-ref', 'HEAD', 'refs/heads/main'], cwd=out, check=True)
    wr = Writer(out)
    tree = {}
    for law, folder, eng, _ in laws:
        files = render(law, folder)
        tree.update(files)
        author = f"{law['name']} ({law['pcode']}) <{law['pcode'].lower()}@law-moj-gov-tw.invalid>"
        wr.commit(author, git_date(law['date']), message(law, folder, eng, docs_date), files)
    import docs  # the README, REPRODUCE.md, corpus.json, tools: one documentation commit
    docfiles = docs.files(laws, docs_date, HERE)
    wr.commit(COMMITTER, git_date(docs_date),
              f'Documentation: README, REPRODUCE, corpus.json, LICENSE and tools\n\n'
              f'Written by Lexifina; no law text changes here.\n', docfiles)
    wr.finish()
    subprocess.run(['git', 'reset', '-q', '--hard', 'main'], cwd=out, check=True)
    if remote:
        subprocess.run(['git', 'remote', 'remove', 'origin'], cwd=out, capture_output=True)
        subprocess.run(['git', 'remote', 'add', 'origin', remote], cwd=out, check=True)
    head = subprocess.run(['git', 'rev-parse', 'main'], cwd=out, capture_output=True, text=True, check=True).stdout.strip()
    return head


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('--docs-date', required=True, help='retrieval day of the data (dates the documentation commit)')
    ap.add_argument('--out', default=os.path.join(os.path.expanduser('~'), 'Documents', 'taiwan-law'))
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--verify-rebuild', action='store_true')
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    if a.verify_rebuild:
        heads = []
        for _ in range(2):
            d = tempfile.mkdtemp(prefix='tw-law-')
            heads.append(build(os.path.join(d, 'r'), a.docs_date, True))
            shutil.rmtree(d, ignore_errors=True)
        print('rebuild heads', heads, 'IDENTICAL' if heads[0] == heads[1] else 'DIFFERENT')
        sys.exit(0 if heads[0] == heads[1] else 1)
    print(build(a.out, a.docs_date, a.offline))


if __name__ == '__main__':
    main()
