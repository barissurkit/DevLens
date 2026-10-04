import { describe, expect, it } from "vitest";
import { paginate, type PageBlock } from "../lib/paginate";

const block = (height: number, extra: Partial<PageBlock> = {}): PageBlock => ({ height, ...extra });
const heightOf = (blocks: PageBlock[], indexes: number[]) => indexes.reduce((sum, i) => sum + blocks[i].height, 0);

describe("paginate", () => {
  it("fills a page and moves a block that does not fit to the next page whole", () => {
    const blocks = [block(40), block(40), block(40)];

    expect(paginate(blocks, 100).pages).toEqual([[0, 1], [2]]);
  });

  it("never exceeds the page height and keeps the reading order", () => {
    const heights = [12, 33, 7, 50, 18, 41, 9, 27, 60, 5, 22, 38, 14, 45, 3, 29];
    const blocks = heights.map((height) => block(height));

    const { pages, oversized } = paginate(blocks, 100);

    expect(oversized).toEqual([]);
    expect(pages.flat()).toEqual(blocks.map((_, i) => i));
    for (const page of pages) expect(heightOf(blocks, page)).toBeLessThanOrEqual(100);
  });

  it("keeps a heading with the block that follows it", () => {
    const blocks = [block(60), block(10, { keepWithNext: true }), block(35)];

    // The heading would fit on page 1 (70 <= 100) but its content would not (105), so both move on.
    expect(paginate(blocks, 100).pages).toEqual([[0], [1, 2]]);
  });

  it("keeps a heading together with a whole run of headings and the content after them", () => {
    const blocks = [block(70), block(8, { keepWithNext: true }), block(8, { keepWithNext: true }), block(30)];

    expect(paginate(blocks, 100).pages).toEqual([[0], [1, 2, 3]]);
  });

  it("starts a new page where asked", () => {
    const blocks = [block(10), block(10, { breakBefore: true }), block(10)];

    expect(paginate(blocks, 100).pages).toEqual([[0], [1, 2]]);
  });

  it("does not create an empty page when the first block asks for a break", () => {
    expect(paginate([block(10, { breakBefore: true }), block(10)], 100).pages).toEqual([[0, 1]]);
  });

  it("gives a block that is taller than a page a page of its own and reports it", () => {
    const blocks = [block(30), block(150), block(30)];

    const plan = paginate(blocks, 100);

    expect(plan.oversized).toEqual([1]);
    expect(plan.pages).toEqual([[0], [1], [2]]);
  });

  it("falls back to placing blocks one by one when heading and content together exceed a page", () => {
    const blocks = [block(60, { keepWithNext: true }), block(60)];

    const plan = paginate(blocks, 100);

    expect(plan.pages).toEqual([[0], [1]]);
    expect(plan.oversized).toEqual([]);
  });

  it("returns no pages for no blocks", () => {
    expect(paginate([], 100)).toEqual({ pages: [], continued: [], oversized: [] });
  });

  it("a block that exactly fills the remaining space stays on the page", () => {
    expect(paginate([block(60), block(40), block(1)], 100).pages).toEqual([[0, 1], [2]]);
  });

  describe("continued sections", () => {
    const title = (height: number, section: string) => block(height, { section, isSectionTitle: true, keepWithNext: true });
    const item = (height: number, section: string) => block(height, { section });

    it("labels a section that runs onto the next page and reserves room for the label", () => {
      const blocks = [title(10, "a"), item(40, "a"), item(40, "a"), item(40, "a")];

      const plan = paginate(blocks, 100, { continuationHeight: 12 });

      expect(plan.pages).toEqual([[0, 1, 2], [3]]);
      expect(plan.continued).toEqual([null, "a"]);
    });

    it("does not label a page that starts a new section or the page that holds a section's title", () => {
      const blocks = [item(75, "intro"), title(10, "b"), item(20, "b"), item(75, "c")];

      const plan = paginate(blocks, 100, { continuationHeight: 12 });

      expect(plan.pages).toEqual([[0], [1, 2], [3]]);
      expect(plan.continued).toEqual([null, null, null]);
    });

    it("counts the label in the space of the page, so the label never causes an overflow", () => {
      // After page 1 the item (95) fits a page, but 95 + label (12) does not, so no label is added rather than overflowing.
      const blocks = [title(10, "a"), item(85, "a"), item(95, "a")];

      const plan = paginate(blocks, 100, { continuationHeight: 12 });

      expect(plan.pages).toEqual([[0, 1], [2]]);
      expect(plan.continued).toEqual([null, null]);
    });

    it("never overflows a page when labels are used, over many random reports", () => {
      let seed = 11;
      const random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
      for (let run = 0; run < 200; run += 1) {
        const blocks: PageBlock[] = [];
        for (let sectionIndex = 0; sectionIndex < 2 + Math.floor(random() * 4); sectionIndex += 1) {
          const section = `s${sectionIndex}`;
          blocks.push(title(8 + Math.floor(random() * 10), section));
          for (let itemIndex = 0; itemIndex < 1 + Math.floor(random() * 10); itemIndex += 1) blocks.push(item(10 + Math.floor(random() * 55), section));
        }
        const plan = paginate(blocks, 100, { continuationHeight: 12 });

        expect(plan.oversized).toEqual([]);
        expect(plan.pages.flat()).toEqual(blocks.map((_, i) => i));
        plan.pages.forEach((page, pageIndex) => {
          const label = plan.continued[pageIndex] ? 12 : 0;
          expect(heightOf(blocks, page) + label).toBeLessThanOrEqual(100);
          if (plan.continued[pageIndex]) {
            // The label only appears where the first block really continues the section from the previous page.
            expect(blocks[page[0]].section).toBe(plan.continued[pageIndex]);
            expect(blocks[page[0]].isSectionTitle).toBeFalsy();
          }
        });
      }
    });
  });

  it("is deterministic for the same input", () => {
    const blocks = [block(20), block(35, { keepWithNext: true }), block(50), block(15), block(80)];

    expect(paginate(blocks, 100)).toEqual(paginate(blocks, 100));
  });

  it("handles many random reports without ever splitting or overflowing", () => {
    let seed = 7;
    const random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let run = 0; run < 200; run += 1) {
      const blocks = Array.from({ length: 5 + Math.floor(random() * 40) }, () =>
        block(5 + Math.floor(random() * 70), { keepWithNext: random() < 0.15, breakBefore: random() < 0.05 }),
      );
      const { pages, oversized } = paginate(blocks, 100);

      expect(oversized).toEqual([]);
      expect(pages.flat()).toEqual(blocks.map((_, i) => i));
      for (const page of pages) expect(heightOf(blocks, page)).toBeLessThanOrEqual(100);
      // A heading never ends a page, unless it is part of a run of headings plus content that is taller than a page
      // (then nothing can keep it together and the blocks are placed one by one).
      const unitHeight = (start: number) => {
        let end = start;
        while (end < blocks.length - 1 && blocks[end].keepWithNext) end += 1;
        return heightOf(blocks, Array.from({ length: end - start + 1 }, (_, k) => start + k));
      };
      pages.forEach((page, pageIndex) => {
        const last = page[page.length - 1];
        if (!blocks[last].keepWithNext || last === blocks.length - 1) return;
        let start = last;
        while (start > 0 && blocks[start - 1].keepWithNext) start -= 1;
        expect(unitHeight(start), `heading ${last} ended page ${pageIndex}`).toBeGreaterThan(100);
      });
    }
  });
});
