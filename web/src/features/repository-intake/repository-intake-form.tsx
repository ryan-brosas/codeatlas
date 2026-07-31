"use client";

import { useState, type FormEvent } from "react";

import { ArchitectureSummary } from "./architecture-summary";
import { analyzeRepository } from "./submit-repository";
import type { RepositoryAnalysisResult } from "./submit-repository";

type SubmissionState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | RepositoryAnalysisResult;

function SubmissionFeedback({ state }: { state: SubmissionState }) {
  if (state.kind === "idle") return null;
  if (state.kind === "submitting") {
    return (
      <p className="mt-5 text-sm font-medium text-blue-800" role="status">
        Analyzing repository…
      </p>
    );
  }
  if (state.kind === "error") {
    return (
      <div
        aria-label="Repository analysis failed"
        className="mt-5 border-l-2 border-red-700 bg-red-50 px-4 py-3"
        role="alert"
      >
        <p className="text-sm font-semibold text-red-950">
          Repository analysis failed
        </p>
        <p className="mt-1 text-sm text-red-900">{state.message}</p>
      </div>
    );
  }
  return <ArchitectureSummary architecture={state.data} />;
}

export function RepositoryIntakeForm() {
  const [state, setState] = useState<SubmissionState>({ kind: "idle" });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const repositoryUrl = formData.get("repository-url");
    if (typeof repositoryUrl !== "string") {
      setState({ kind: "error", message: "Enter a public GitHub repository URL." });
      return;
    }

    setState({ kind: "submitting" });
    setState(await analyzeRepository(repositoryUrl));
  }

  const isSubmitting = state.kind === "submitting";

  return (
    <>
      <form
      className="mt-10 max-w-2xl"
      aria-label="Repository analysis"
      onSubmit={handleSubmit}
    >
      <label
        className="mb-3 block text-sm font-semibold text-slate-900"
        htmlFor="repository-url"
      >
        Public GitHub repository URL
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          aria-invalid={state.kind === "error"}
          className="min-h-12 flex-1 rounded-md border border-slate-400 bg-slate-50 px-4 text-base text-slate-950 outline-none transition-colors placeholder:text-slate-500 focus:border-blue-700 focus:ring-2 focus:ring-blue-200 disabled:cursor-wait disabled:bg-slate-100"
          disabled={isSubmitting}
          id="repository-url"
          name="repository-url"
          placeholder="https://github.com/owner/repository"
          required
          type="url"
        />
        <button
          className="min-h-12 rounded-md bg-slate-950 px-6 text-sm font-semibold text-slate-50 transition-colors hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-700 focus:ring-offset-2 disabled:cursor-wait disabled:bg-slate-600"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Analyzing repository…" : "Analyze repository"}
        </button>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        Public TypeScript and JavaScript repositories will be supported first.
      </p>
      </form>
      <SubmissionFeedback state={state} />
    </>
  );
}
