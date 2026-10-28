# Reproducing lexifina/taiwan-law

## Source and terms
- 全國法規資料庫, Ministry of Justice, https://law.moj.gov.tw/. Retrieved 2026-10-28.
- Terms: 政府網站資料開放宣告 (https://law.moj.gov.tw/Service/Copyright.aspx): Open Government Data License v1,
  free reuse including derived works, with attribution.
- robots.txt (checked 2026-10-28, no AI-agent rules, no crawl-delay):

  ```
  User-agent: *
  Disallow: /
  Allow: /News/NewsDetail.aspx
  Allow: /LawClass/LawAll.aspx
  Allow: /SearchEngineSitemap.aspx
  Sitemap: https://law.moj.gov.tw/SearchEngineSitemap.aspx
  ```

  Only the allowed `/LawClass/LawAll.aspx` was fetched for the build. During the terms check, before the robots
  check was complete, the API documentation page `/api/swagger` (index and `/api/swagger/docs/v1`) was opened once
  each; nothing from it is used.
- Requests for the build: 6 pages (the five laws here plus 民法, which was then left out), one at a time, curl with
  `--compressed` (gzip) and the User-Agent `LexifinaBot/1.0`.

## Pages (sha256 of the decoded page)

| Code | Law | URL | sha256 |
|---|---|---|---|
| A0000001 | 中華民國憲法 | `https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0000001` | `78358f2946999d86ea40a81a30691adae4682c893fd163d824434b3f0858b0d9` |
| A0000002 | 中華民國憲法增修條文 | `https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0000002` | `c4f22421d75ee6eaebf437887edd1f094f5658610d6d4aefc7f849e02914edfd` |
| B0010001 | 民事訴訟法 | `https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=B0010001` | `9b1f735eac8ca223edf47582341ef3da7c8e8f66fbb2d409326a4e3b973cad45` |
| C0010001 | 刑事訴訟法 | `https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0010001` | `bd82aa1577d787e0f7ab2123f3de6fe4e78c8df40eee071fa317276b452ae0bf` |
| C0000001 | 中華民國刑法 | `https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001` | `d1f2aec199fa44574a237799b579980747382bcc1a570cd245a0f5ef54f95c73` |

## Commands, in order

```
python scripts/taiwan-law/build.py --docs-date 2026-10-28 --out C:/Users/alany/Documents/taiwan-law
python scripts/taiwan-law/check_repo.py C:/Users/alany/Documents/taiwan-law --write
python scripts/taiwan-law/build.py --docs-date 2026-10-28 --verify-rebuild
python scripts/taiwan-law/test_repo.py --repo C:/Users/alany/Documents/taiwan-law --record
python scripts/test_corpus.py C:/Users/alany/Documents/taiwan-law tools/on_date.py
```

`--offline` rebuilds from the saved pages (`scripts/taiwan-law/.cache/*.html.gz`, gzip, not in git). The documentation
commit is dated by the retrieval day (`--docs-date`), so a rebuild on another day gives the same hashes.

Tools: Python 3.12 (standard library only), git 2.x (`git fast-import`), curl 8.x.

## Builder files (git blob hashes)

| File | Blob |
|---|---|
| `builder/build.py` | `4a588475aa5b5098c6691dd56439a81bd1f24eea` |
| `builder/docs.py` | `f4f99456cb757bf92febf4c49b7d5895b532b12a` |
| `builder/check_repo.py` | `012716eb9eb88f864505cd5e0f23af92e7c8fc04` |
| `builder/on_date.py` | `4ecb2b75b480b9b47df10d42673e7d58c3c34fbf` |
| `builder/test_repo.py` | `22606962b9ab299807fc40338e45645044a6781e` |

## Decisions made by hand
- Scope: 中華民國憲法, 中華民國憲法增修條文, 中華民國刑法, 民事訴訟法, 刑事訴訟法. 民法 dropped because its page includes
  text not yet in force (see README).
- Dates: the page's 修正日期 or 公布日期 at 12:00 +0800, labelled `In-force-basis:`; no commencement rule applied.
- Constitution: 1947-01-01 clamped to 1970-01-01 in the git date.
- Indent classes (line-0004/0006) and the CSS paragraph numbers (show-number) are presentation, not text: dropped.

## Checks (last run)

```
{
  "check_repo": {
    "byte_mismatches": 0,
    "laws": {
      "code-of-civil-procedure": {
        "byte_mismatches": 0,
        "files": 801,
        "stream_chars": 60356,
        "stream_equal": true
      },
      "code-of-criminal-procedure": {
        "byte_mismatches": 0,
        "files": 713,
        "stream_chars": 68110,
        "stream_equal": true
      },
      "constitution": {
        "byte_mismatches": 0,
        "files": 177,
        "stream_chars": 8217,
        "stream_equal": true
      },
      "constitution-additional-articles": {
        "byte_mismatches": 0,
        "files": 14,
        "stream_chars": 3511,
        "stream_equal": true
      },
      "criminal-code": {
        "byte_mismatches": 0,
        "files": 423,
        "stream_chars": 35074,
        "stream_equal": true
      }
    },
    "stream_mismatches": 0
  },
  "smoke": {
    "passed": 6,
    "results": [
      {
        "detail": "criminal-code/article/271.md lines by {'中華民國刑法 (C0000001)'}",
        "ok": true,
        "test": "blame names the law"
      },
      {
        "detail": "criminal-code/article/185-3.md from 2026-07-22; constitution-additional-articles/article/4.md from 2005-06-10; constitution/article/1.md from 1947-01-01",
        "ok": true,
        "test": "on-date tool gives the text from the page date, nothing before"
      },
      {
        "detail": "5 law commits carry In-force in order; 0 tags",
        "ok": true,
        "test": "In-force on every law commit, in order; tags resolve"
      },
      {
        "detail": "only the documentation commit is by Lexifina; 5 law commits",
        "ok": true,
        "test": "only the documentation commit is by Lexifina"
      },
      {
        "detail": "5 README commands ran and printed output",
        "ok": true,
        "test": "README commands run"
      },
      {
        "detail": "5 commits parse",
        "ok": true,
        "test": "trailers parse"
      }
    ],
    "total": 6
  }
}
```

## AI
Built by Claude Code with Claude Opus 5.5 (`claude-opus-5-5`), which wrote the builder, checks and documentation.
No AI wrote or edited legal text, and no model runs at build time: the text is copied from the pages by code.
