import type {
  GitHubPortfolioAnalysis,
  InterpretationUnavailableReason,
  PublicPortfolioInterpretationResult,
} from "../lib/types";

interface PortfolioInterpretationSectionProps {
  analysis: GitHubPortfolioAnalysis;
  interpretation: PublicPortfolioInterpretationResult;
}

const UNAVAILABLE_COPY: Record<InterpretationUnavailableReason, string> = {
  not_configured: "AI yorumu şu anda kullanılamıyor. Deterministic portföy analizi aşağıda kullanılabilir.",
  insufficient_evidence: "AI yorumu için yeterli başarılı repository evidence'ı oluşmadı.",
  timeout: "AI yorumu geçici olarak kullanılamıyor.",
  rate_limit: "AI yorumu geçici olarak kullanılamıyor.",
  unavailable: "AI yorumu geçici olarak kullanılamıyor.",
  upstream_error: "AI yorumu geçici olarak kullanılamıyor.",
  invalid_response: "AI yorumu bu analiz için kullanılamadı.",
};

export function PortfolioInterpretationSection({ analysis, interpretation }: PortfolioInterpretationSectionProps) {
  return (
    <section aria-labelledby="ai-interpretation-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">Optional AI layer</p>
      <h3 id="ai-interpretation-heading" className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">AI Yorumu</h3>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
        Bu bölüm, DevLens&apos;in ölçtüğü deterministic evidence sonuçlarını açıklar; skorları veya evidence&apos;ı değiştirmez.
      </p>
      {interpretation.status === "available" ? (
        <AvailableInterpretation analysis={analysis} interpretation={interpretation.interpretation} />
      ) : (
        <p className="mt-6 rounded-xl bg-slate-50 px-4 py-4 text-sm leading-6 text-slate-600">{UNAVAILABLE_COPY[interpretation.reason]}</p>
      )}
    </section>
  );
}

function AvailableInterpretation({ analysis, interpretation }: { analysis: GitHubPortfolioAnalysis; interpretation: Extract<PublicPortfolioInterpretationResult, { status: "available" }>['interpretation'] }) {
  const signalLabels = new Map(analysis.aggregation.portfolio_signals.map((signal) => [signal.key, signal.label]));
  return (
    <div className="mt-6 space-y-6 text-sm leading-6 text-slate-700">
      <p className="max-w-3xl break-words">{interpretation.summary}</p>
      <ExplanationGroup title="Güçlü Evidence Sinyalleri" explanations={interpretation.strength_explanations} signalLabels={signalLabels} emptyMessage="Bu analiz için AI açıklamalı güçlü sinyal bulunmuyor." />
      <ExplanationGroup title="İyileştirme Fırsatları" explanations={interpretation.improvement_explanations} signalLabels={signalLabels} emptyMessage="Bu analiz için AI açıklamalı iyileştirme sinyali bulunmuyor." />
      {interpretation.technology_context && <ContextBlock title="Technology Context" text={interpretation.technology_context} />}
      {interpretation.project_area_context && <ContextBlock title="Project Area Context" text={interpretation.project_area_context} />}
      {interpretation.limitations_note && <ContextBlock title="AI interpretation note" text={interpretation.limitations_note} />}
    </div>
  );
}

function ExplanationGroup({ title, explanations, signalLabels, emptyMessage }: { title: string; explanations: Array<{ signal_key: string; explanation: string }>; signalLabels: Map<string, string>; emptyMessage: string }) {
  return (
    <section aria-labelledby={`${title}-ai-heading`}>
      <h4 id={`${title}-ai-heading`} className="text-base font-semibold text-slate-950">{title}</h4>
      {explanations.length > 0 ? (
        <ul className="mt-3 space-y-3">
          {explanations.map((item) => <li key={item.signal_key} className="rounded-xl bg-slate-50 p-4"><p className="font-medium text-slate-900">{signalLabels.get(item.signal_key) || "Evidence sinyali"}</p><p className="mt-1 break-words">{item.explanation}</p></li>)}
        </ul>
      ) : <p className="mt-3 text-slate-500">{emptyMessage}</p>}
    </section>
  );
}

function ContextBlock({ title, text }: { title: string; text: string }) {
  return <section aria-labelledby={`${title}-ai-heading`} className="rounded-xl border border-slate-200 p-4"><h4 id={`${title}-ai-heading`} className="font-semibold text-slate-950">{title}</h4><p className="mt-2 break-words">{text}</p></section>;
}
