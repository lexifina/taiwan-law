# Taiwan law in git

Laws of the Republic of China (Taiwan), one file per article. The current text of the five laws in the first
table is as the Ministry of Justice's 全國法規資料庫 (law.moj.gov.tw) shows it; the laws in the "Past versions"
table have every version the Legislative Yuan's 立法院法律系統 shows, one commit per version, authored by the
amending law and dated by the day it took effect.

| Folder | Law | Code | Page date | Articles |
|---|---|---|---|---|
| `constitution/` | 中華民國憲法 (Constitution of the Republic of China (Taiwan)) | A0000001 | 公布日期 1947-01-01 | 175 |
| `constitution-additional-articles/` | 中華民國憲法增修條文 (Additional Articles of the Constitution of the Republic of China) | A0000002 | 修正日期 2005-06-10 | 12 |
| `code-of-civil-procedure/` | 民事訴訟法 (Code of Civil Procedure) | B0010001 | 修正日期 2023-11-29 | 800 |
| `code-of-criminal-procedure/` | 刑事訴訟法 (Code of Criminal Procedure) | C0010001 | 修正日期 2026-05-13 | 712 |
| `criminal-code/` | 中華民國刑法 (Criminal Code of the Republic of China) | C0000001 | 修正日期 2026-07-22 | 422 |

<!-- ly-history -->
## Past versions (立法院法律系統)

For the laws below, every version that 立法院法律系統 (https://lis.ly.gov.tw/, the Legislative Yuan's law system) shows was added on 2026-11-02, as one block of commits per law appended after the earlier history (ruling: older versions found late are appended at the end, never rewritten in place).

| Folder | Law | Versions | First in force | Last in force |
|---|---|---|---|---|
| `criminal-code/` | 中華民國刑法 (Criminal Code of the Republic of China) | 60 | 1935-07-01 | 2026-07-24 |
| `company-act/` | 公司法 (Company Act) | 29 | 1931-07-01 | 2025-12-28 |
| `labor-standards-act/` | 勞動基準法 (Labor Standards Act) | 24 | 1984-08-01 | 2024-08-02 |
| `code-of-civil-procedure/` | 民事訴訟法 (Code of Civil Procedure) | 28 | 1930-12-28 | 2023-12-01 |
| `code-of-criminal-procedure/` | 刑事訴訟法 (Code of Criminal Procedure) | 57 | 1928-09-01 | 2026-05-15 |
| `income-tax-act/` | 所得稅法 (Income Tax Act) | 73 | 1943-02-19 | 2026-01-01 |

- **One commit per version.** Each commit holds the whole text of the law as the LY record shows it for that version (one file per article, `structure.md` for the order and headings). The author is the amending law (`<law><action> (<promulgation day>)`, e.g. `公司法修正 (2018-08-01)`) at an address that cannot exist, so `git blame` names the amendment that last changed a line.
- **Dates.** `In-force:` (and the author date) is the commencement day (施行) the LY record states; where it states none, the third day counted from promulgation (中央法規標準法 §13: a law that takes effect on promulgation takes effect from the third day counted from that day). Where a later version would take effect before an earlier amendment it already contains, it is dated by that amendment's day (the trailer `In-force-basis:` says so). Days before 1970 are clamped to 1970-01-01 in the git date only. The commit (committer) date is the day the block was appended, so `git log --before` does not work here: use the `In-force:` trailer or `tools/on_date.py`, which read it.
- **Laws already published from law.moj.gov.tw.** Their block ends with a commit (kind `publisher-text`, same `In-force:` as the last version) that puts back, unchanged, the files published on 2026-10-28, so the current text is still the 全國法規資料庫 text. The two official publishers print some articles differently (mostly punctuation); that commit lists how many.
- **Articles with a later commencement.** Where an amendment leaves single articles to commence on a day set later (施行日期由行政院定之), the LY version (and so the commit) carries them from the version's day; the commit message quotes the record's dates.
- **Future text.** A version whose day is after the retrieval day is not on `main`.

<!-- /ly-history -->

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

- **Past versions of the other laws.** The laws not in the "Past versions" table have one commit each: the
  current text, dated by its page date, so blame credits the whole text to that date.
- **民法 (Civil Code, B0000001)** is left out: its page says some articles are not yet in force (art. 1223 as
  amended 2026-08-17 takes effect six months after promulgation; art. 166-1 has no commencement day), so its text is
  not the text in force today; past versions from 立法院法律系統 carry the same articles (art. 166-1 since 2000), so
  they are left out too.
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

This repository is a Lexifina build. It is not an official publication; where it differs from the text the
responsible authority published, the official text prevails.

Past versions: 立法院網站資料開放宣告 (https://www.ly.gov.tw/Pages/List.aspx?nodeid=10772): the material on the Legislative Yuan's sites, to the extent it is protected by copyright, is offered free of charge, non-exclusively and sub-licensably, for reproduction, adaptation, editing, public transmission and other uses without time or territorial limit and without further permission; use must state the source.

資料來源：立法院法律系統 (https://lis.ly.gov.tw/)。
