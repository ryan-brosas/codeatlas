"use server";

import createClient from "openapi-fetch";

import type { components, paths } from "../../lib/api/generated";

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

export async function analyzeRepository(
  repositoryUrl: string,
): Promise<RepositoryAnalysisResult> {
  const client = createClient<paths>({
    baseUrl: process.env.CODEATLAS_ANALYSIS_URL ?? "http://127.0.0.1:8000",
  });

  try {
    const { data, error } = await client.POST("/v1/architecture", {
      body: { repository_url: repositoryUrl },
    });

    if (data) {
      return { kind: "success", data };
    }
    return {
      kind: "error",
      message: error?.error.message ?? "Repository analysis failed.",
    };
  } catch {
    return {
      kind: "error",
      message: "The analysis service is unavailable. Try again.",
    };
  }
}


export async function askRepositoryQuestion(
  repositoryUrl: string,
  question: string,
): Promise<RepositoryQuestionResult> {
  const client = createClient<paths>({
    baseUrl: process.env.CODEATLAS_ANALYSIS_URL ?? "http://127.0.0.1:8000",
  });

  try {
    const { data, error } = await client.POST("/v1/questions", {
      body: { repository_url: repositoryUrl, question },
    });

    if (data) {
      return { kind: "success", data };
    }
    return {
      kind: "error",
      message: error?.error.message ?? "Repository question failed.",
    };
  } catch {
    return {
      kind: "error",
      message: "The analysis service is unavailable. Try again.",
    };
  }
}


export async function analyzeRepositoryImpact(
  repositoryUrl: string,
  question: string,
): Promise<RepositoryImpactResult> {
  const client = createClient<paths>({
    baseUrl: process.env.CODEATLAS_ANALYSIS_URL ?? "http://127.0.0.1:8000",
  });

  try {
    const { data, error } = await client.POST("/v1/impact", {
      body: { repository_url: repositoryUrl, question },
    });
    if (data) return { kind: "success", data };
    return {
      kind: "error",
      message: error?.error.message ?? "Change-impact analysis failed.",
    };
  } catch {
    return {
      kind: "error",
      message: "The analysis service is unavailable. Try again.",
    };
  }
}
