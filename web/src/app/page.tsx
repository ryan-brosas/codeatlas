import { AnalysisContract, Capabilities } from "../features/landing/landing-sections";
import { RepositoryIntakeForm } from "../features/repository-intake/repository-intake-form";

export default function Home() {
  return (
    <main className="mx-auto min-h-screen max-w-[1440px] px-6 pb-16 pt-6 sm:px-8 lg:px-12">
      <header className="flex items-center justify-between border-b border-slate-300 pb-5">
        <a className="text-lg font-semibold tracking-[-0.03em]" href="#top">
          CodeAtlas
        </a>
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-slate-600">
          Repository intelligence
        </p>
      </header>

      <section
        className="grid gap-12 border-b border-slate-300 py-16 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)] lg:gap-20 lg:py-24"
        id="top"
      >
        <div>
          <p className="mb-6 font-mono text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
            Source before speculation
          </p>
          <h1 className="max-w-[16ch] text-5xl font-semibold leading-[0.98] tracking-[-0.055em] text-slate-950 sm:text-6xl lg:text-7xl">
            Understand a codebase before you change it.
          </h1>
          <p className="mt-8 max-w-[62ch] text-lg leading-8 text-slate-700">
            CodeAtlas turns unfamiliar repositories into navigable architecture,
            source-cited answers, and practical change-impact guidance.
          </p>
          <RepositoryIntakeForm />
        </div>
        <AnalysisContract />
      </section>

      <Capabilities />
    </main>
  );
}
