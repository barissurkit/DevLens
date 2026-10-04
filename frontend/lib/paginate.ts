export interface PageBlock {
  /** Measured height of the block in the same unit as the page height (pixels). */
  height: number;
  /** A heading-like block that must not end a page: it moves to the next page together with what follows it. */
  keepWithNext?: boolean;
  /** Start a new page before this block. */
  breakBefore?: boolean;
  /** The section this block belongs to, so a section that runs onto another page can be labelled there. */
  section?: string;
  /** The block that carries the section's own title (it never gets a "continued" label). */
  isSectionTitle?: boolean;
}

export interface PagePlan {
  /** Indexes of the blocks on each page, in reading order. */
  pages: number[][];
  /** For each page, the section that carries over from the previous page and needs a "continued" label, or null. */
  continued: Array<string | null>;
  /** Blocks taller than a whole page; they get a page of their own and are reported so the design can stay within bounds. */
  oversized: number[];
}

export interface PaginateOptions {
  /** Height reserved at the top of a page for the "continued" label of a section that runs over. */
  continuationHeight?: number;
}

/**
 * Packs measured blocks into pages. A block is never split: if it does not fit in the space left on the page it
 * starts the next one, so every paragraph or card is either wholly on a page or wholly on the following one.
 * Blocks flagged `keepWithNext` are kept on the same page as the block after them. When a section's items continue
 * on a new page, room is reserved for a "continued" label and the section is reported in `continued`.
 */
export function paginate(blocks: PageBlock[], pageHeight: number, options: PaginateOptions = {}): PagePlan {
  const continuationHeight = options.continuationHeight ?? 0;
  const pages: number[][] = [];
  const continued: Array<string | null> = [];
  const oversized: number[] = [];
  let current: number[] = [];
  let currentContinued: string | null = null;
  let used = 0;
  let lastSection: string | undefined;

  const startPage = () => {
    if (current.length > 0) {
      pages.push(current);
      continued.push(currentContinued);
    }
    current = [];
    currentContinued = null;
    used = 0;
  };

  /** Space the label needs if `first` opens a page in the middle of its section; 0 when no label is needed. */
  const labelFor = (first: PageBlock, unitHeight: number): number => {
    if (continuationHeight <= 0 || current.length > 0 || !first.section || first.isSectionTitle) return 0;
    if (first.section !== lastSection) return 0;
    return unitHeight + continuationHeight <= pageHeight ? continuationHeight : 0;
  };

  const place = (blockIndex: number, label: number) => {
    if (label > 0) {
      currentContinued = blocks[blockIndex].section ?? null;
      used += label;
    }
    current.push(blockIndex);
    used += blocks[blockIndex].height;
    lastSection = blocks[blockIndex].section;
  };

  // The unit that has to stay together: a run of keepWithNext blocks plus the block that follows it.
  let index = 0;
  while (index < blocks.length) {
    let end = index;
    while (end < blocks.length - 1 && blocks[end].keepWithNext) end += 1;
    const unit = blocks.slice(index, end + 1);
    const unitHeight = unit.reduce((sum, block) => sum + block.height, 0);

    if (blocks[index].breakBefore) startPage();

    if (unitHeight > pageHeight) {
      // Too tall to keep together: place the blocks one by one, still without splitting any single block.
      for (let offset = 0; offset < unit.length; offset += 1) {
        const block = unit[offset];
        const blockIndex = index + offset;
        if (block.height > pageHeight) {
          oversized.push(blockIndex);
          startPage();
          place(blockIndex, 0);
          startPage();
          continue;
        }
        if (used + block.height > pageHeight) startPage();
        place(blockIndex, labelFor(block, block.height));
      }
    } else {
      if (used + unitHeight > pageHeight) startPage();
      const label = labelFor(unit[0], unitHeight);
      for (let offset = 0; offset < unit.length; offset += 1) place(index + offset, offset === 0 ? label : 0);
    }
    index = end + 1;
  }
  startPage();
  return { pages, continued, oversized };
}
