"use client";

import { analyzeRepositoryImpact } from "./submit-repository";
import type { ChangeImpactReport } from "./submit-repository";
import { useRepositoryRequest } from "./use-repository-request";

function ImpactReportView({ report }: { report: ChangeImpactReport }) {
  if (report.status !== "found") {
    return (
      <div className="mt-4 border-l-2 border-amber-600 bg-amber-50 px-4 py-3" role="status">
        <p className="text-sm font-semibold text-amber-950">
          No implementation candidate found
        </p>
        <p className="mt-1 text-sm text-amber-900">
          CodeAtlas did not infer a change location without source evidence.
        </p>
      </div>
    );
  }

  const candidate = report.candidates[0];
  return (
    <section
      aria-labelledby="likely-change-impact"
      className="mt-4 border-l-2 border-violet-700 bg-violet-50 px-4 py-3"
      role="status"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-violet-950" id="likely-change-impact">
          Likely change impact
        </h3>
        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-violet-800">
          {report.location_confidence === "high"
            ? "High"
            : report.location_confidence === "medium"
              ? "Medium"
              : "Low"} location confidence
        </p>
      </div>
      {candidate ? (
        <div className="mt-3 border border-violet-200 bg-white px-3 py-2">
          <p className="font-mono text-sm font-semibold text-slate-950">
            {candidate.citation.symbol ?? candidate.citation.path}
          </p>
          <p className="mt-1 font-mono text-xs text-violet-800">
            {candidate.citation.path} · L{candidate.citation.start_line}
          </p>
        </div>
      ) : null}
      {report.impacts.length > 0 ? (
        <ul className="mt-3 space-y-2" aria-label="Potentially impacted modules">
          {report.impacts.map((impact) => (
            <li className="border border-violet-200 bg-white px-3 py-2" key={impact.path}>
              <p className="font-mono text-sm text-slate-950">{impact.path}</p>
              <p className="mt-1 text-xs text-violet-800">
                {impact.depth === 1
                  ? `Direct impact · L${impact.evidence.start_line}`
                  : `Transitive impact · depth ${impact.depth} · L${impact.evidence.start_line}`}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-violet-900">No dependent modules were resolved.</p>
      )}
      <ul className="mt-3 space-y-1 text-xs text-violet-900" aria-label="Impact limitations">
        {report.warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </section>
  );
}

export function RepositoryImpactForm({ repositoryUrl }: { repositoryUrl: string }) {
  const { state, handleSubmit } = useRepositoryRequest(
    "change-description",
    (question) => analyzeRepositoryImpact(repositoryUrl, question),
  );

  return (
    <form
      aria-label="Change impact"
      className="mt-5 border-t border-slate-300 pt-5"
      onSubmit={handleSubmit}
    >
      <label
        className="block text-sm font-semibold text-slate-900"
        htmlFor="change-description"
      >
        Change description
      </label>
      <div className="mt-2 flex flex-col gap-2 sm:flex-row">
        <input
          className="min-h-11 flex-1 border border-slate-400 bg-white px-3 text-sm text-slate-950 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-200 disabled:cursor-wait disabled:bg-slate-100"
          disabled={state.kind === "submitting"}
          id="change-description"
          name="change-description"
          placeholder="Change session validation"
          required
          type="text"
        />
        <button
          className="min-h-11 bg-violet-800 px-4 text-sm font-semibold text-white hover:bg-slate-950 focus:outline-none focus:ring-2 focus:ring-violet-700 focus:ring-offset-2 disabled:cursor-wait disabled:bg-slate-600"
          disabled={state.kind === "submitting"}
          type="submit"
        >
          {state.kind === "submitting" ? "Tracing impact…" : "Analyze impact"}
        </button>
      </div>
      {state.kind === "submitting" ? (
        <p className="mt-3 text-sm text-violet-800" role="status">
          Tracing verified repository relationships…
        </p>
      ) : null}
      {state.kind === "error" ? (
        <div aria-label="Change-impact analysis failed" className="mt-4 border-l-2 border-red-700 bg-red-50 px-4 py-3" role="alert">
          <p className="text-sm font-semibold text-red-950">Change-impact analysis failed</p>
          <p className="mt-1 text-sm text-red-900">{state.message}</p>
        </div>
      ) : null}
      {state.kind === "success" ? <ImpactReportView report={state.data} /> : null}
    </form>
  );
}
