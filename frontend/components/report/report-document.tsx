"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { paginate, type PagePlan } from "../../lib/paginate";
import type { ReportModel } from "../../lib/report";
import { BrandMark, BrandWordmark } from "../brand-mark";
import { buildReportBlocks, SECTION_TITLES } from "./report-blocks";

const MM = 96 / 25.4;
/** A4 sheet and the area of it that holds the flowing content (header and footer sit in the margins). */
export const SHEET_WIDTH_PX = Math.round(210 * MM);
export const CONTENT_WIDTH_MM = 178;
export const CONTENT_HEIGHT_PX = Math.floor(258 * MM);
/** Room kept at the top of a page for the "(devamı)" label of a section that runs over from the page before. */
export const CONTINUATION_HEIGHT_PX = Math.ceil(10 * MM);

const dateFormatter = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul" });

interface ReportDocumentProps {
  model: ReportModel;
  createdAt: Date;
  url: string;
  /** Called once the pages are laid out, with the plan (page count, blocks that were too tall). */
  onLayout?: (plan: PagePlan) => void;
}

const MODE_LABEL = { ozet: "Özet rapor", detay: "Ayrıntılı rapor" } as const;

export function ReportDocument({ model, createdAt, url, onLayout }: ReportDocumentProps) {
  const blocks = useMemo(() => buildReportBlocks(model), [model]);
  const measureRef = useRef<HTMLDivElement>(null);
  const [plan, setPlan] = useState<PagePlan | null>(null);
  const [zoom, setZoom] = useState(1);

  // Measure every block at its final width and pack whole blocks into pages. Done after the fonts are ready,
  // because a different font changes line breaks and therefore heights.
  useEffect(() => {
    let cancelled = false;
    const measure = () => {
      const container = measureRef.current;
      if (cancelled || !container) return;
      const nodes = Array.from(container.querySelectorAll<HTMLElement>("[data-block]"));
      const next = paginate(
        nodes.map((node, index) => ({
          height: Math.ceil(node.getBoundingClientRect().height),
          keepWithNext: blocks[index].keepWithNext,
          breakBefore: blocks[index].breakBefore,
          section: blocks[index].section,
          isSectionTitle: blocks[index].isSectionTitle,
        })),
        CONTENT_HEIGHT_PX,
        { continuationHeight: CONTINUATION_HEIGHT_PX },
      );
      setPlan(next);
      onLayout?.(next);
    };
    const fonts = typeof document !== "undefined" ? document.fonts : undefined;
    if (fonts?.ready) void fonts.ready.then(measure);
    else window.setTimeout(measure, 0);
    return () => { cancelled = true; };
  }, [blocks, onLayout]);

  // On a narrow screen the A4 sheets are scaled down to fit (never in print).
  useEffect(() => {
    const update = () => setZoom(Math.min(1, (window.innerWidth - 24) / SHEET_WIDTH_PX));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  const totalPages = (plan?.pages.length ?? 0) + 1;

  return (
    <div className="report-root" data-report-pages={plan ? plan.pages.length + 1 : undefined} data-report-oversized={plan ? plan.oversized.length : undefined}>
      <div ref={measureRef} aria-hidden="true" className="report-measure" style={{ width: `${CONTENT_WIDTH_MM}mm` }}>
        {blocks.map((block) => <div key={block.key} data-block className="pb-[3.2mm]">{block.node}</div>)}
      </div>

      <div className="report-sheets" style={{ ["--report-zoom" as string]: zoom }}>
        <Sheet>
          <Cover model={model} createdAt={createdAt} url={url} />
        </Sheet>
        {plan?.pages.map((page, pageIndex) => (
          <Sheet key={pageIndex}>
            <PageFrame model={model} pageNumber={pageIndex + 2} totalPages={totalPages} createdAt={createdAt} />
            <div className="report-flow" style={{ width: `${CONTENT_WIDTH_MM}mm` }}>
              {plan.continued[pageIndex] && (
                <div className="report-continued" style={{ height: CONTINUATION_HEIGHT_PX }}>
                  <p className="text-[10.5pt] font-semibold text-slate-600">{SECTION_TITLES[plan.continued[pageIndex] as string]} <span className="font-normal text-slate-400">(devamı)</span></p>
                </div>
              )}
              {page.map((blockIndex) => <div key={blocks[blockIndex].key} data-report-block className="pb-[3.2mm]">{blocks[blockIndex].node}</div>)}
            </div>
          </Sheet>
        ))}
      </div>
    </div>
  );
}

function Sheet({ children }: { children: React.ReactNode }) {
  return <section className="report-sheet">{children}</section>;
}

function PageFrame({ model, pageNumber, totalPages, createdAt }: { model: ReportModel; pageNumber: number; totalPages: number; createdAt: Date }) {
  return (
    <>
      <header className="report-page-header">
        <div className="flex items-center gap-2"><BrandMark className="h-5 w-5" idPrefix={`page-${pageNumber}`} /><BrandWordmark className="text-[10pt]" /><span className="text-[8.5pt] text-slate-400">· {MODE_LABEL[model.mode]}</span></div>
        <p className="text-[8.5pt] font-medium text-slate-600">{model.displayName === `@${model.username}` ? model.displayName : `${model.displayName} · @${model.username}`}</p>
      </header>
      <footer className="report-page-footer">
        <p>{dateFormatter.format(createdAt)}</p>
        <p>Sayfa {pageNumber} / {totalPages}</p>
      </footer>
    </>
  );
}

function Cover({ model, createdAt, url }: { model: ReportModel; createdAt: Date; url: string }) {
  return (
    <div className="flex h-full flex-col px-[18mm] py-[18mm]">
      <div className="flex items-center gap-4">
        <BrandMark className="h-14 w-14" idPrefix="cover" />
        <BrandWordmark className="text-[26pt]" />
      </div>

      <div className="mt-auto">
        <p className="text-[10pt] font-semibold uppercase tracking-[0.22em] text-indigo-700">Portföy Analiz Raporu</p>
        <p className="mt-1 text-[10pt] text-slate-500">{MODE_LABEL[model.mode]}</p>
        <div className="mt-8 flex items-center gap-5">
          {model.avatarUrl && (
            // eslint-disable-next-line @next/next/no-img-element -- small external GitHub avatar, printed as is
            <img src={model.avatarUrl} alt="" width={84} height={84} className="h-[22mm] w-[22mm] rounded-2xl border border-slate-200 object-cover" />
          )}
          <div className="min-w-0">
            <h1 className="break-words text-[30pt] font-semibold leading-tight tracking-tight text-slate-950">{model.displayName}</h1>
            <p className="mt-1 text-[14pt] text-slate-600">@{model.username}</p>
          </div>
        </div>

        <div className="mt-12 flex items-end gap-6">
          <p className={`text-[64pt] font-semibold leading-none tracking-tight ${model.tone?.text ?? "text-slate-950"}`}>
            {model.hasScore ? model.score : "—"}
            {model.hasScore && <span className="text-[20pt] text-slate-500"> / 100</span>}
          </p>
          {model.tone && <span className={`mb-2 rounded-full px-4 py-1.5 text-[12pt] font-semibold ${model.tone.badge}`}>{model.tone.label}</span>}
        </div>

        {model.dimensions.length > 0 && (
          <ul className="mt-8 max-w-[120mm] space-y-3">
            {model.dimensions.map((dimension) => (
              <li key={dimension.key}>
                <div className="flex justify-between text-[10pt]"><span className="font-medium text-slate-800">{dimension.label}</span><span className="text-slate-600">{dimension.earned.toLocaleString("tr-TR", { maximumFractionDigits: 1 })} / {dimension.possible}</span></div>
                <div className="mt-1 h-2 rounded-full bg-slate-200"><div className="h-2 rounded-full bg-indigo-600" style={{ width: `${dimension.percent}%` }} /></div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-auto border-t border-slate-300 pt-5 text-[9.5pt] leading-relaxed text-slate-600">
        <p><span className="font-semibold text-slate-800">Oluşturulma:</span> {dateFormatter.format(createdAt)}</p>
        <p><span className="font-semibold text-slate-800">Kaynak:</span> {url}</p>
        <p className="mt-2 text-[8.5pt] text-slate-500">Skor, herkese açık GitHub repository&apos;lerindeki ölçülebilir sinyallere dayanır ve deterministik kurallarla hesaplanır. Bir geliştiricinin yetkinliğinin tamamını ölçmez.</p>
      </div>
    </div>
  );
}
