"use server";

import { headers } from "next/headers";
import createClient from "openapi-fetch";

import type { components, paths } from "../../lib/api/generated";
import {
  AdmissionError,
  clientKeyFromHeaders,
  repositoryRateKey,
  RequestAdmission,
} from "./request-admission";

export type ArchitectureView = components["schemas"]["ArchitectureView"];
export type CitedAnswer = components["schemas"]["CitedAnswer"];
export type ChangeImpactReport = components["schemas"]["ChangeImpactReport"];

export type RepositoryAnalysisResult =
  | { kind: "success"; data: ArchitectureView }
  | { kind: "error"; message: string };

export type RepositoryImpactResult =
  | { kind: "success"; data: ChangeImpactReport }
  | { kind: "error"; message: string };

export type RepositoryQuestionResult =
  | { kind: "success"; data: CitedAnswer }
  | { kind: "error"; message: string };

const admission = new RequestAdmission({
  clientLimit: 12,
  repositoryLimit: 6,
  windowMs: 60_000,
  maxConcurrent: 2,
  maxTrackedKeys: 2_000,
  timeoutMs: 30_000,
});

function analysisClient() {
  return createClient<paths>({
    baseUrl: process.env.CODEATLAS_ANALYSIS_URL ?? "http://127.0.0.1:8000",
  });
}

async function requestClientKey() {
  try {
    const requestHeaders = await headers();
    return clientKeyFromHeaders(
      requestHeaders.get("x-forwarded-for"),
      requestHeaders.get("x-real-ip"),
    );
  } catch {
    return "unknown";
  }
}

async function controlledRequest<T>(
  repositoryUrl: string,
  operation: (signal: AbortSignal) => Promise<T>,
) {
  return admission.run(
    {
      clientKey: await requestClientKey(),
      repositoryKey: repositoryRateKey(repositoryUrl),
    },
    operation,
  );
}

function failureMessage(error: unknown, fallback: string) {
  return error instanceof AdmissionError ? error.message : fallback;
}

export async function analyzeRepository(
  repositoryUrl: string,
): Promise<RepositoryAnalysisResult> {
  try {
    const { data, error } = await controlledRequest(repositoryUrl, (signal) =>
      analysisClient().POST("/v1/architecture", {
        body: { repository_url: repositoryUrl },
        signal,
      }),
    );
    if (data) return { kind: "success", data };
    return {
      kind: "error",
      message: error?.error.message ?? "Repository analysis failed.",
    };
  } catch (error) {
    return {
      kind: "error",
      message: failureMessage(
        error,
        "The analysis service is unavailable. Try again.",
      ),
    };
  }
}

export async function askRepositoryQuestion(
  repositoryUrl: string,
  question: string,
): Promise<RepositoryQuestionResult> {
  try {
    const { data, error } = await controlledRequest(repositoryUrl, (signal) =>
      analysisClient().POST("/v1/questions", {
        body: { repository_url: repositoryUrl, question },
        signal,
      }),
    );
    if (data) return { kind: "success", data };
    return {
      kind: "error",
      message: error?.error.message ?? "Repository question failed.",
    };
  } catch (error) {
    return {
      kind: "error",
      message: failureMessage(
        error,
        "The analysis service is unavailable. Try again.",
      ),
    };
  }
}

export async function analyzeRepositoryImpact(
  repositoryUrl: string,
  question: string,
): Promise<RepositoryImpactResult> {
  try {
    const { data, error } = await controlledRequest(repositoryUrl, (signal) =>
      analysisClient().POST("/v1/impact", {
        body: { repository_url: repositoryUrl, question },
        signal,
      }),
    );
    if (data) return { kind: "success", data };
    return {
      kind: "error",
      message: error?.error.message ?? "Change-impact analysis failed.",
    };
  } catch (error) {
    return {
      kind: "error",
      message: failureMessage(
        error,
        "The analysis service is unavailable. Try again.",
      ),
    };
  }
}
