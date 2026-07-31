// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { RepositoryImpactForm } from "./repository-impact-form";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("presents candidate location, impact depth, confidence, and uncertainty", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      new Response(
        JSON.stringify({
          query: "session validation function",
          status: "found",
          candidates: [
            {
              kind: "symbol",
              basis: "verified_source",
              citation: {
                path: "src/core/session.ts",
                start_line: 1,
                end_line: 1,
                symbol: "validateSession",
              },
              score: 2,
              matched_terms: ["function", "session", "validation"],
              method: "lexical",
            },
          ],
          impacts: [
            {
              path: "src/login.ts",
              depth: 1,
              evidence: {
                path: "src/login.ts",
                start_line: 1,
                end_line: 1,
                symbol: "validateSession",
              },
            },
          ],
          location_confidence: "high",
          warnings: [
            "Dependency proximity identifies possible impact, not certainty.",
          ],
          truncated: false,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    ),
  );
  render(
    <RepositoryImpactForm repositoryUrl="https://github.com/example/project" />,
  );

  fireEvent.change(screen.getByLabelText("Change description"), {
    target: { value: "session validation function" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Change impact" }));

  expect(await screen.findByText("Likely change impact")).toBeTruthy();
  expect(screen.getByText("validateSession")).toBeTruthy();
  expect(screen.getByText("src/core/session.ts · L1")).toBeTruthy();
  expect(screen.getByText("src/login.ts")).toBeTruthy();
  expect(screen.getByText("Direct impact · L1")).toBeTruthy();
  expect(screen.getByText("High location confidence")).toBeTruthy();
  expect(
    screen.getByText(
      "Dependency proximity identifies possible impact, not certainty.",
    ),
  ).toBeTruthy();
});
