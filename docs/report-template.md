# Printed report template

DevLens can turn an analysis into a printable report: `/u/<login>/rapor?tur=ozet` (summary) or `?tur=detay`
(detailed). The result page offers both behind its **Yazdır / PDF** button; the report page prints, or saves as PDF,
from the browser's print dialog. It is built from the analysis data (no AI interpretation, no personal workspace data), so
anyone can open the report of any public portfolio.

| Report | Pages | Contents |
|---|---|---|
| Summary (`ozet`) | cover + 1-2 | overview sentence, score, the four scoring dimensions, up to three strengths, the top three improvements and the points they could add, technologies and project areas, analysis scope, notes and limits |
| Detailed (`detay`) | summary + about one page per three repositories + method | everything above, then every analyzed repository (score, category, 15 checks, technologies), excluded and failed repositories, and the scoring method (every rule and weight) |

## Why a template and not the printed web page

Printing the screen layout means fighting the browser: blank pages, cards cut in half, buttons that have to be
hidden, and the browser's own header and footer. The report is instead a fixed-size A4 document that is filled in:

- Every sheet is exactly 210 x 297 mm (`.report-sheet`). The page rule `@page report { size: A4; margin: 0 }` removes
  the margins, which also removes the browser's header/footer; the report draws its own header (logo, name, report
  type) and footer (date, "Sayfa n / N").
- The content is split into **blocks** (`components/report/report-blocks.tsx`): a title, a paragraph, a card, a
  table row. A block is never divided.
- `ReportDocument` renders all blocks invisibly at the final width, measures them, and `paginate()`
  (`lib/paginate.ts`) packs whole blocks into the content area of each page. A block that does not fit in the space
  left starts the next page, so a paragraph is either entirely on a page or entirely on the next one.
- Titles are kept with the block after them (`keepWithNext`), so a heading never ends a page on its own. When a list
  runs onto another page, that page starts with "<section title> (devamı)" (space for it is reserved in advance).
  The repository and method sections start on a new page (`breakBefore`).

## Guarantees that are tested

- `tests/paginate.test.ts`: blocks are never split or reordered, no page is filled beyond its height, headings are
  kept with their content, the "continued" label never causes an overflow; checked on hundreds of random reports.
- `e2e/report.spec.ts` (real Chrome): for the recorded portfolio, a portfolio with no analyzed repository, one with 30
  repositories and one with very long names, descriptions and notes, **every element** of every page stays inside the
  content area (nothing below it, above it or past the right margin), no block is taller than a page, the generated
  PDF has exactly one PDF page per sheet, and page numbers run `2 / N ... N / N`.

## Changing the report

- Content and order: `buildReportBlocks()` in `components/report/report-blocks.tsx`. Give a block a key starting
  with `title-` to open a section; the blocks after it belong to that section. Keep every block clearly shorter than a
  page (the 30-repository test fails with `data-report-oversized` > 0 otherwise); a card with unbounded content must be
  cut down (as technologies are: six per repository).
- Data: `lib/report.ts` (`buildReportModel`) turns the analysis into what the report shows.
- Page size and margins: constants at the top of `components/report/report-document.tsx` and the `.report-*` rules in
  `app/globals.css`; the content height (258 mm) and the flow position (21 mm from the top) must stay consistent.
- The report is always printed and shown in the light palette, whichever theme the visitor uses.
