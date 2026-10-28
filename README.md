# Taiwan law in git (current text only)

The current text of five central laws of the Republic of China (Taiwan), one file per article, as the Ministry of
Justice's 全國法規資料庫 (law.moj.gov.tw) shows them. Each law is one commit, authored by the law and dated by the date
its page states.

| Folder | Law | Code | Page date | Articles |
|---|---|---|---|---|
| `constitution/` | 中華民國憲法 (Constitution of the Republic of China (Taiwan)) | A0000001 | 公布日期 1947-01-01 | 175 |
| `constitution-additional-articles/` | 中華民國憲法增修條文 (Additional Articles of the Constitution of the Republic of China) | A0000002 | 修正日期 2005-06-10 | 12 |
| `code-of-civil-procedure/` | 民事訴訟法 (Code of Civil Procedure) | B0010001 | 修正日期 2023-11-29 | 800 |
| `code-of-criminal-procedure/` | 刑事訴訟法 (Code of Criminal Procedure) | C0010001 | 修正日期 2026-05-13 | 712 |
| `criminal-code/` | 中華民國刑法 (Criminal Code of the Republic of China) | C0000001 | 修正日期 2026-07-22 | 422 |

## Questions as git commands

| Question | Command |
|---|---|
| What does article 271 of the Criminal Code say? | `cat criminal-code/article/271.md` |
| Which law and date does a line come from? | `git blame criminal-code/article/271.md` |
| The whole law in the page's order | `python tools/on_date.py 2026-10-28 criminal-code` |
| One article on a date | `python tools/on_date.py 2026-10-28 criminal-code 185-3` |
| Which laws are here, and their dates | `git log --format="%an  %(trailers:key=In-force,valueonly,separator=)"` |

Use the `In-force:` trailer (or `tools/on_date.py`) rather than `git log --before`: the constitution's commit date
is clamped to 1970 because git cannot store earlier dates.

## Dates: which one we use

- The commit date is the date the law's page states, at 12:00 Asia/Taipei (UTC+8): **修正日期** (the day the last
  amendment was promulgated) or, for a law never amended, **公布日期** (promulgation). The same day is in `In-force:`,
  with `In-force-basis: page-amended-date` or `page-promulgated-date` to say where it came from.
- It is **not** a commencement day. Under 中央法規標準法 §13 a law that takes effect on promulgation takes effect
  from the third day counted from that day, and many amendments set their own day; the page states neither. The
  Constitution was promulgated on 1 January 1947 and took effect on 25 December 1947 (憲法實施之準備程序); the page
  gives only the first date, and the commit is dated by it (clamped to 1970-01-01 in the git date).

## What this record does not show

- **Past versions.** law.moj.gov.tw keeps every past version (沿革, LawHistory.aspx, LawOldVer.aspx) and offers an
  open-data API (/api/), but its robots.txt disallows them:

  ```
  User-agent: *
  Disallow: /
  Allow: /News/NewsDetail.aspx
  Allow: /LawClass/LawAll.aspx
  Allow: /SearchEngineSitemap.aspx
  Sitemap: https://law.moj.gov.tw/SearchEngineSitemap.aspx
  ```

  Only `/LawClass/LawAll.aspx`, the current full text, was fetched. So each law has ONE commit and blame credits the
  whole text to the law's latest page date, not to the act that wrote each line.
- **民法 (Civil Code, B0000001)** is left out: its page says some articles are not yet in force (art. 1223 as
  amended 2026-08-17 takes effect six months after promulgation; art. 166-1 has no commencement day), so its text is
  not the text in force today, and the text in force is only on a disallowed page.
- **Attachments.** Criminal Code art. 185-3 has a PDF attachment (a table of drug concentration values); it is marked
  `(本條文有附件)` in `structure.md` and not copied.
- **Indentation.** The site indents list items (一、二、) by CSS class; the files keep the words, one paragraph or item
  per line, without the indent.

## How it is checked

`check_repo.py` (in `builder/`) re-reads every saved page and compares, for each law:
1. every file in the repo byte for byte with the parse of the page (0 mismatches required);
2. an independent word stream: the letters and digits (casefolded) of every text node in the page's law content
   area, taken by a separate minimal extractor that knows no structure, against the same stream from the repo files
   in `structure.md` order (0 mismatches required).

A second build from the same saved pages must give the same commit hashes.

## What "author" means

The author of each law commit is the law, with an address that cannot exist (`c0000001@law-moj-gov-tw.invalid`), so
`git blame` names it. The committer is Lexifina. Only the final documentation commit is authored by Lexifina.

## How it is built

`python builder/build.py --docs-date 2026-10-28` fetches the five pages (or reads the saved copies with `--offline`)
and writes the history through one `git fast-import`. See REPRODUCE.md.

## Licence

The law texts are not protected by copyright (著作權法 §9: constitutions, laws and orders are not the subject of
copyright). The database pages are offered under the 政府資料開放授權條款－第1版 (Open Government Data License,
version 1.0), which requires attribution:

資料來源：法務部「全國法規資料庫」(https://law.moj.gov.tw/)，依「政府資料開放授權條款－第1版」提供。
Source: Laws & Regulations Database of the Republic of China (Taiwan), Ministry of Justice (https://law.moj.gov.tw/), used under the Open Government Data License, version 1.0.

This repository is a private Lexifina build. It is not an official publication; where it differs from the text the
responsible authority published, the official text prevails.
