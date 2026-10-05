import type { ReactNode } from "react";
import type { ReportCheckGroup, ReportDimension, ReportModel, ReportRepository } from "../../lib/report";

/** One unit of the report that is never split: a heading, a paragraph, a card or a table row. */
export interface ReportBlockSpec {
  key: string;
  node: ReactNode;
  keepWithNext?: boolean;
  breakBefore?: boolean;
  /** The section this block belongs to (the id of the title block above it). */
  section?: string;
  isSectionTitle?: boolean;
}

/** Section titles by id; a section that runs onto another page is labelled "<title> (devamı)" there. */
export const SECTION_TITLES: Record<string, string> = {
  overview: "Genel değerlendirme",
  dimensions: "Puanlama boyutları",
  strengths: "Güçlü yönler",
  priorities: "Öncelikli iyileştirmeler",
  tech: "Teknolojiler ve proje alanları",
  scope: "Analiz kapsamı",
  notes: "Notlar ve sınırlar",
  repositories: "Repository ayrıntıları",
  excluded: "Hariç tutulan repository'ler",
  failures: "Analiz edilemeyen repository'ler",
  method: "Puanlama yöntemi",
};

const formatPoints = (value: number) => value.toLocaleString("tr-TR", { maximumFractionDigits: 1 });

function SectionTitle({ children, sub }: { children: ReactNode; sub?: string }) {
  return (
    <div className="pt-1">
      <h2 className="text-[15pt] font-semibold leading-tight tracking-tight text-slate-950">{children}</h2>
      {sub && <p className="mt-1 text-[9pt] leading-snug text-slate-500">{sub}</p>}
      <div className="mt-2 h-px bg-slate-300" />
    </div>
  );
}

function Paragraph({ children, muted = false }: { children: ReactNode; muted?: boolean }) {
  return <p className={`text-[10pt] leading-relaxed ${muted ? "text-slate-500" : "text-slate-800"}`}>{children}</p>;
}

function Bar({ percent, tone = "bg-brand-600" }: { percent: number; tone?: string }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-slate-200">
      <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} />
    </div>
  );
}

function ScoreCard({ model }: { model: ReportModel }) {
  return (
    <div className="flex items-center gap-6 rounded-xl border border-slate-300 bg-slate-50 px-6 py-5">
      <div>
        <p className="text-[8pt] font-semibold uppercase tracking-[0.16em] text-slate-500">Portföy kanıt skoru</p>
        <p className={`mt-1 text-[36pt] font-semibold leading-none tracking-tight ${model.tone?.text ?? "text-slate-950"}`}>
          {model.hasScore ? model.score : "—"}
          {model.hasScore && <span className="text-[14pt] text-slate-500"> / 100</span>}
        </p>
      </div>
      <div className="min-w-0 flex-1">
        {model.tone && <span className={`inline-block rounded-full px-3 py-1 text-[10pt] font-semibold ${model.tone.badge}`}>{model.tone.label}</span>}
        <p className="mt-2 text-[9pt] leading-snug text-slate-600">
          {model.hasScore
            ? `${model.analyzedRepositoryCount} başarılı repository üzerinden, deterministik kurallarla hesaplandı.`
            : "Skor için en az iki repository'nin başarıyla analiz edilmesi gerekir."}
        </p>
      </div>
    </div>
  );
}

function DimensionRow({ dimension }: { dimension: ReportDimension }) {
  return (
    <div className="rounded-lg border border-slate-200 px-4 py-3">
      <div className="flex items-baseline justify-between gap-4">
        <p className="text-[10.5pt] font-semibold text-slate-900">{dimension.label}</p>
        <p className="text-[10pt] font-semibold text-slate-900">{formatPoints(dimension.earned)} <span className="font-normal text-slate-500">/ {dimension.possible}</span></p>
      </div>
      <div className="mt-2"><Bar percent={dimension.percent} /></div>
      {dimension.description && <p className="mt-2 text-[8.5pt] leading-snug text-slate-500">{dimension.description}</p>}
    </div>
  );
}

function Tags({ items }: { items: Array<{ name: string; count: number }> }) {
  return (
    <ul className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <li key={item.name} className="rounded-full border border-slate-300 bg-slate-50 px-2.5 py-0.5 text-[9pt] text-slate-700">
          {item.name} <span className="text-slate-500">· {item.count}</span>
        </li>
      ))}
    </ul>
  );
}

function CheckGroup({ group }: { group: ReportCheckGroup }) {
  return (
    <div className="min-w-0">
      <p className="text-[8pt] font-semibold uppercase tracking-wide text-slate-500">{group.title}</p>
      <ul className="mt-1 space-y-0.5">
        {group.checks.map((check) => (
          <li key={check.key} className="flex items-start gap-1.5 text-[8.5pt] leading-snug">
            <span aria-hidden="true" className={`mt-px w-3 shrink-0 text-center font-bold ${check.present ? "text-emerald-700" : "text-slate-400"}`}>{check.present ? "✓" : "–"}</span>
            <span className={check.present ? "text-slate-800" : "text-slate-500"}>
              {check.label}
              <span className="sr-only">{check.present ? " (var)" : " (yok)"}</span>
              {check.uncertain && <span className="text-slate-400"> (*)</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RepositoryCard({ repository }: { repository: ReportRepository }) {
  const partial = repository.groups.some((group) => group.checks.some((check) => check.uncertain));
  return (
    <div className="rounded-xl border border-slate-300 px-4 py-3.5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate text-[11pt] font-semibold text-slate-950">{repository.name}</p>
          <p className="mt-0.5 text-[8.5pt] text-slate-500">{[repository.category, repository.language].filter(Boolean).join(" · ")}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className={`text-[16pt] font-semibold leading-none ${repository.tone.text}`}>{repository.score}<span className="text-[9pt] text-slate-500"> / 100</span></p>
          <p className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[8pt] font-semibold ${repository.tone.badge}`}>{repository.tone.label}</p>
        </div>
      </div>
      {repository.description && <p className="mt-2 line-clamp-2 text-[9pt] leading-snug text-slate-700">{repository.description}</p>}
      <div className="mt-3 grid grid-cols-3 gap-4 border-t border-slate-200 pt-3">
        {repository.groups.map((group) => <CheckGroup key={group.title} group={group} />)}
      </div>
      {(repository.technologies.length > 0 || partial) && (
        <div className="mt-3 border-t border-slate-200 pt-2 text-[8.5pt] leading-snug text-slate-600">
          {repository.technologies.length > 0 && <p><span className="font-semibold text-slate-700">Teknolojiler:</span> {repository.technologies.join(", ")}{repository.extraTechnologies > 0 ? ` ve ${repository.extraTechnologies} tane daha` : ""}</p>}
          {partial && <p className="mt-0.5 text-slate-500">(*) Dosya ağacı eksik alındığı için bu dosya görülmemiş olabilir.</p>}
        </div>
      )}
    </div>
  );
}

/** The blocks of the report, in reading order. The cover is a separate page and is not part of this flow. */
export function buildReportBlocks(model: ReportModel): ReportBlockSpec[] {
  const blocks: ReportBlockSpec[] = [];
  let currentSection: string | undefined;
  // A block whose key starts with "title-" opens a section; the blocks after it belong to that section.
  const add = (key: string, node: ReactNode, options: Partial<ReportBlockSpec> = {}) => {
    const isSectionTitle = key.startsWith("title-");
    if (isSectionTitle) currentSection = key.slice("title-".length);
    blocks.push({ key, node, section: currentSection, isSectionTitle, ...options });
  };

  add("title-overview", <SectionTitle>{SECTION_TITLES.overview}</SectionTitle>, { keepWithNext: true });
  add("overview", <Paragraph>{model.overview}</Paragraph>);
  add("score", <ScoreCard model={model} />);

  if (model.dimensions.length > 0) {
    add("title-dimensions", <SectionTitle sub="Her boyut kendi içinde 0–100 olarak, toplam skora katkısı puanla gösterilir.">{SECTION_TITLES.dimensions}</SectionTitle>, { keepWithNext: true });
    model.dimensions.forEach((dimension) => add(`dimension-${dimension.key}`, <DimensionRow dimension={dimension} />));
  }

  add("title-strengths", <SectionTitle sub="Başarıyla analiz edilen repository'lerin en az yarısında görülen sinyaller.">{SECTION_TITLES.strengths}</SectionTitle>, { keepWithNext: true });
  if (model.strengths.length === 0) add("strengths-empty", <Paragraph muted>Portföy genelinde tekrar eden güçlü bir kanıt sinyali belirlenmedi.</Paragraph>);
  model.strengths.forEach((item) => add(`strength-${item.key}`, (
    <div className="rounded-lg border-l-4 border-emerald-500 bg-slate-50 px-4 py-2.5">
      <p className="text-[9.5pt] leading-snug text-slate-800">{item.message}</p>
      <div className="mt-2 flex items-center gap-3"><div className="flex-1"><Bar percent={(item.detected_repository_count / Math.max(1, item.analyzed_repository_count)) * 100} tone="bg-emerald-500" /></div><p className="text-[8.5pt] font-semibold text-slate-700">{item.detected_repository_count} / {item.analyzed_repository_count} repository</p></div>
    </div>
  )));

  add("title-priorities", <SectionTitle sub="Puan, kuralın ağırlığı × eksik repository oranıdır.">{SECTION_TITLES.priorities}</SectionTitle>, { keepWithNext: true });
  if (model.priorities.length === 0) add("priorities-empty", <Paragraph muted>Skoru artıracak belirgin bir eksik bulunmadı.</Paragraph>);
  model.priorities.forEach((item, index) => add(`priority-${item.key}`, (
    <div className="flex items-center gap-3 rounded-lg border border-slate-200 px-4 py-2.5">
      <span aria-hidden="true" className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-[9pt] font-semibold text-white">{index + 1}</span>
      <div className="min-w-0 flex-1">
        <p className="text-[10pt] font-semibold text-slate-900">{item.label}</p>
        <p className="text-[8.5pt] text-slate-500">{item.analyzedRepositories} repository&apos;nin {item.missingRepositories} tanesinde eksik</p>
      </div>
      <p className="shrink-0 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[9pt] font-semibold text-emerald-800">+{formatPoints(item.points)} puan</p>
    </div>
  )));
  if (model.priorities.length > 0 && model.potentialGain > 0) add("priorities-total", <Paragraph>Bu adımların tamamı skoru yaklaşık <strong>+{model.potentialGain} puan</strong> artırabilir.</Paragraph>);

  if (model.technologies.length > 0 || model.areas.length > 0) {
    add("title-tech", <SectionTitle>{SECTION_TITLES.tech}</SectionTitle>, { keepWithNext: true });
    if (model.technologies.length > 0) add("technologies", (<div><p className="mb-1.5 text-[8.5pt] font-semibold text-slate-600">Birden fazla repository&apos;de tespit edilen teknolojiler</p><Tags items={model.technologies} /></div>));
    if (model.areas.length > 0) add("areas", (<div><p className="mb-1.5 text-[8.5pt] font-semibold text-slate-600">Tekrar eden proje alanları</p><Tags items={model.areas} /></div>));
  }

  add("title-scope", <SectionTitle>{SECTION_TITLES.scope}</SectionTitle>, { keepWithNext: true });
  add("scope", (
    <dl className="grid grid-cols-3 gap-3">
      {model.scope.map((item) => (
        <div key={item.label} className="rounded-lg border border-slate-200 px-3 py-2">
          <dt className="text-[8pt] text-slate-500">{item.label}</dt>
          <dd className={`mt-0.5 text-[13pt] font-semibold ${item.warn ? "text-amber-700" : "text-slate-900"}`}>{item.value}</dd>
        </div>
      ))}
    </dl>
  ));

  add("title-notes", <SectionTitle>{SECTION_TITLES.notes}</SectionTitle>, { keepWithNext: true });
  model.limitations.forEach((text, index) => add(`limitation-${index}`, <Paragraph muted>• {text}</Paragraph>));
  add("disclaimer", <Paragraph muted>• Skor, herkese açık GitHub repository&apos;lerindeki ölçülebilir sinyallere dayanır ve deterministik kurallarla hesaplanır. Bir geliştiricinin yetkinliğinin, deneyiminin ya da özel çalışmalarının tamamını ölçmez.</Paragraph>);

  if (model.mode === "detay") {
    add("title-repositories", <SectionTitle sub={`${model.repositories.length} repository, en yüksek skordan başlayarak sıralandı.`}>{SECTION_TITLES.repositories}</SectionTitle>, { keepWithNext: true, breakBefore: true });
    if (model.repositories.length === 0) add("repositories-empty", <Paragraph muted>Başarıyla analiz edilen repository bulunmuyor.</Paragraph>);
    model.repositories.forEach((repository) => add(`repository-${repository.name}`, <RepositoryCard repository={repository} />));

    if (model.excluded.length > 0) {
      add("title-excluded", <SectionTitle sub="Fork ve arşivlenmiş repository'ler analiz dışı bırakılır.">{SECTION_TITLES.excluded}</SectionTitle>, { keepWithNext: true });
      model.excluded.forEach((item) => add(`excluded-${item.name}`, <Paragraph>{item.name} <span className="text-slate-500">— {item.reason}</span></Paragraph>));
    }
    if (model.failures.length > 0) {
      add("title-failures", <SectionTitle>{SECTION_TITLES.failures}</SectionTitle>, { keepWithNext: true });
      model.failures.forEach((item) => add(`failure-${item.name}`, <Paragraph>{item.name} <span className="text-slate-500">— {item.message}</span></Paragraph>));
    }

    add("title-method", <SectionTitle sub="Skor, aşağıdaki kuralların ağırlığı ile kuralın görüldüğü repository oranının çarpımlarının toplamıdır.">{SECTION_TITLES.method}</SectionTitle>, { keepWithNext: true, breakBefore: true });
    let lastDimension = "";
    model.rules.forEach((rule) => {
      const first = rule.dimension !== lastDimension;
      lastDimension = rule.dimension;
      add(`rule-${rule.dimension}-${rule.label}`, (
        <div>
          {first && <p className="mb-1 mt-2 text-[8.5pt] font-semibold uppercase tracking-wide text-slate-500">{rule.dimension}</p>}
          <div className="flex items-baseline justify-between border-b border-slate-100 py-1 text-[9.5pt]"><span className="text-slate-800">{rule.label}</span><span className="font-semibold text-slate-900">{rule.weight} puan</span></div>
        </div>
      ));
    });
    add("method-note", <Paragraph muted>Örnek: ağırlığı 10 olan bir kural, analiz edilen repository&apos;lerin yarısında görülüyorsa 5 puan getirir. Son 12 ayda güncelleme kuralı analiz zamanına göre hesaplandığından zamanla değişebilir.</Paragraph>);
  }

  return blocks;
}
