"use client";

import { askRepositoryQuestion } from "./submit-repository";
import type { CitedAnswer } from "./submit-repository";
import { useRepositoryRequest } from "./use-repository-request";

function AnswerResult({ answer }: { answer: CitedAnswer }) {
  if (answer.status !== "answered") {
    return (
      <div className="mt-4 border-l-2 border-amber-600 bg-amber-50 px-4 py-3" role="status">
        <p className="text-sm font-semibold text-amber-950">
          {answer.status === "unsupported"
            ? "Unsupported question"
            : "Insufficient source evidence"}
        </p>
        <p className="mt-1 text-sm text-amber-900">
          CodeAtlas did not generate an answer.
        </p>
      </div>
    );
  }

  return (
    <section
      aria-labelledby="verified-source-answer"
      className="mt-4 border-l-2 border-emerald-700 bg-emerald-50 px-4 py-3"
      role="status"
    >
      <h3
        className="text-sm font-semibold text-emerald-950"
        id="verified-source-answer"
      >
        Verified source answer
      </h3>
      <ul className="mt-3 space-y-3">
        {answer.facts.map((fact) => (
          <li className="text-sm text-emerald-950" key={fact.text}>
            <p>{fact.text}</p>
            <ul className="mt-1 flex flex-wrap gap-2" aria-label="Source citations">
              {fact.citations.map((citation) => (
                <li
                  className="font-mono text-xs text-emerald-800"
                  key={`${citation.path}:${citation.start_line}:${citation.symbol ?? ""}`}
                >
                  {citation.path} · L{citation.start_line}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs font-semibold uppercase tracking-[0.12em] text-emerald-800">
        No model inference used
      </p>
    </section>
  );
}

export function RepositoryQuestionForm({
  repositoryUrl,
}: {
  repositoryUrl: string;
}) {
  const { state, handleSubmit } = useRepositoryRequest(
    "question",
    (question) => askRepositoryQuestion(repositoryUrl, question),
  );

  return (
    <form
      aria-label="Repository question"
      className="mt-5 border-t border-slate-300 pt-5"
      onSubmit={handleSubmit}
    >
      <label className="block text-sm font-semibold text-slate-900" htmlFor="question">
        Question
      </label>
      <div className="mt-2 flex flex-col gap-2 sm:flex-row">
        <input
          className="min-h-11 flex-1 border border-slate-400 bg-white px-3 text-sm text-slate-950 outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-200 disabled:cursor-wait disabled:bg-slate-100"
          disabled={state.kind === "submitting"}
          id="question"
          name="question"
          placeholder="Where is authentication implemented?"
          required
          type="text"
        />
        <button
          className="min-h-11 bg-blue-800 px-4 text-sm font-semibold text-white hover:bg-slate-950 focus:outline-none focus:ring-2 focus:ring-blue-700 focus:ring-offset-2 disabled:cursor-wait disabled:bg-slate-600"
          disabled={state.kind === "submitting"}
          type="submit"
        >
          {state.kind === "submitting" ? "Searching source…" : "Ask question"}
        </button>
      </div>
      {state.kind === "submitting" ? (
        <p className="mt-3 text-sm text-blue-800" role="status">
          Searching verified source evidence…
        </p>
      ) : null}
      {state.kind === "error" ? (
        <div
          aria-label="Repository question failed"
          className="mt-4 border-l-2 border-red-700 bg-red-50 px-4 py-3"
          role="alert"
        >
          <p className="text-sm font-semibold text-red-950">Repository question failed</p>
          <p className="mt-1 text-sm text-red-900">{state.message}</p>
        </div>
      ) : null}
      {state.kind === "success" ? <AnswerResult answer={state.data} /> : null}
    </form>
  );
}
