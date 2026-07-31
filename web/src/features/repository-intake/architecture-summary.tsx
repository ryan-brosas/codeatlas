import { RepositoryImpactForm } from "./repository-impact-form";
import { RepositoryQuestionForm } from "./repository-question-form";
import type { ArchitectureView } from "./submit-repository";

function countLabel(count: number, singular: string) {
  return `${count} ${singular}${count === 1 ? "" : "s"}`;
}

export function ArchitectureSummary({
  architecture,
}: {
  architecture: ArchitectureView;
}) {
  return (
    <>
      <section
      aria-labelledby="architecture-ready"
      className="mt-6 border-l-2 border-blue-700 bg-blue-50 px-4 py-4"
      role="status"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2
            className="text-sm font-semibold text-slate-950"
            id="architecture-ready"
          >
            Architecture ready
          </h2>
          <p className="mt-1 font-mono text-sm text-slate-800">
            {architecture.repository.id}
          </p>
        </div>
        <p className="font-mono text-xs text-blue-900">
          {architecture.revision.slice(0, 12)}
        </p>
      </div>
      <p className="mt-3 text-xs font-semibold uppercase tracking-[0.12em] text-blue-800">
        {countLabel(architecture.modules.length, "module")} ·{" "}
        {countLabel(architecture.relationships.length, "relationship")} ·{" "}
        {countLabel(architecture.limitations.length, "limitation")}
      </p>
      <div className="mt-4 grid gap-3">
        {architecture.modules.map((module) => (
          <article
            className="border border-blue-200 bg-white px-3 py-3"
            key={module.path}
          >
            <h3 className="font-mono text-sm font-semibold text-slate-950">
              {module.path}
            </h3>
            {module.symbols.length > 0 ? (
              <ul className="mt-2 flex flex-wrap gap-2" aria-label={`Symbols in ${module.path}`}>
                {module.symbols.map((symbol) => (
                  <li
                    className="bg-slate-100 px-2 py-1 font-mono text-xs text-slate-800"
                    key={`${symbol.name}:${symbol.line}`}
                  >
                    {symbol.name}
                    <span className="ml-2 text-slate-500">
                      {symbol.kind} · L{symbol.line}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-slate-600">No exported symbols</p>
            )}
          </article>
        ))}
      </div>
      {architecture.limitations.length > 0 ? (
        <p className="mt-3 text-xs text-amber-900">
          {countLabel(architecture.limitations.length, "limitation")} retained as
          explicit evidence.
        </p>
      ) : null}
      </section>
      <RepositoryQuestionForm
        repositoryUrl={architecture.repository.canonical_url}
      />
      <RepositoryImpactForm
        repositoryUrl={architecture.repository.canonical_url}
      />
    </>
  );
}
