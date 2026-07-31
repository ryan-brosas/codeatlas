const capabilities = [
  {
    label: "01 / Architecture",
    title: "See how the repository is shaped.",
    description:
      "Trace modules, symbols, and dependencies without flattening the codebase into a folder list.",
  },
  {
    label: "02 / Evidence",
    title: "Ask questions that point back to source.",
    description:
      "Keep verified file and symbol evidence separate from model inference, with citations you can inspect.",
  },
  {
    label: "03 / Impact",
    title: "Understand a change before making it.",
    description:
      "Locate the right implementation boundary and review the likely blast radius before touching code.",
  },
] as const;

export function AnalysisContract() {
  return (
    <aside className="self-end border-l-2 border-blue-700 pl-6" aria-label="Analysis contract">
      <p className="font-mono text-xs uppercase tracking-[0.14em] text-slate-600">
        Analysis contract
      </p>
      <dl className="mt-6 space-y-5">
        <div>
          <dt className="text-sm text-slate-600">Verified facts</dt>
          <dd className="mt-1 font-mono text-sm text-slate-950">file + symbol evidence</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-600">Model inference</dt>
          <dd className="mt-1 font-mono text-sm text-slate-950">explicitly identified</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-600">Provider boundary</dt>
          <dd className="mt-1 font-mono text-sm text-slate-950">replaceable adapter</dd>
        </div>
      </dl>
    </aside>
  );
}

export function Capabilities() {
  return (
    <section className="py-16 lg:py-20" id="workflow">
      <div className="mb-12 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
            What it makes visible
          </p>
          <h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-4xl">
            A repository, with its reasoning attached.
          </h2>
        </div>
        <p className="max-w-md text-sm leading-6 text-slate-600">
          The first release stays focused on understanding code. Autonomous changes and pull requests remain outside the boundary.
        </p>
      </div>

      <div className="grid border-t border-slate-300 md:grid-cols-3">
        {capabilities.map((capability) => (
          <article
            className="border-b border-slate-300 py-8 md:border-b-0 md:border-r md:px-8 md:first:pl-0 md:last:border-r-0 md:last:pr-0"
            key={capability.label}
          >
            <p className="font-mono text-xs uppercase tracking-[0.14em] text-slate-500">
              {capability.label}
            </p>
            <h3 className="mt-6 max-w-[22ch] text-xl font-semibold tracking-[-0.025em] text-slate-950">
              {capability.title}
            </h3>
            <p className="mt-4 max-w-[42ch] text-base leading-7 text-slate-600">
              {capability.description}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
