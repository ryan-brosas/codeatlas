// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Home from "./page";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("CodeAtlas landing page", () => {
  it("offers public repository analysis", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Understand a codebase before you change it.",
      }),
    ).toBeTruthy();

    const repositoryUrl = screen.getByLabelText("Public GitHub repository URL");
    expect(repositoryUrl.getAttribute("type")).toBe("url");
    expect(repositoryUrl.getAttribute("required")).not.toBeNull();
    expect(
      screen.getByRole("button", { name: "Analyze repository" }),
    ).toBeTruthy();
  });

  it("announces analysis and presents source-cited architecture", async () => {
    let resolveRequest: (response: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            resolveRequest = resolve;
          }),
      ),
    );
    render(<Home />);

    fireEvent.change(screen.getByLabelText("Public GitHub repository URL"), {
      target: { value: "https://github.com/Vercel/Next.js" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Repository analysis" }));

    const submittingButton = screen.getByRole("button", {
      name: "Analyzing repository…",
    }) as HTMLButtonElement;
    expect(submittingButton.disabled).toBe(true);
    expect(screen.getByRole("status").textContent).toContain(
      "Analyzing repository…",
    );

    resolveRequest(
      new Response(
        JSON.stringify({
          repository: {
            id: "github.com/vercel/next.js",
            host: "github.com",
            owner: "vercel",
            name: "next.js",
            canonical_url: "https://github.com/vercel/next.js",
          },
          revision: "0123456789abcdef0123456789abcdef01234567",
          modules: [
            {
              path: "src/index.ts",
              language: "typescript",
              parse_status: "complete",
              symbols: [{ name: "run", kind: "function", line: 1 }],
            },
          ],
          relationships: [],
          limitations: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    expect(await screen.findByText("Architecture ready")).toBeTruthy();
    expect(screen.getByText("github.com/vercel/next.js")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("1 module");
    expect(screen.getByText("src/index.ts")).toBeTruthy();
    expect(screen.getByText("run")).toBeTruthy();
  });

  it("announces a typed repository error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            error: {
              code: "unsupported_repository_host",
              message: "Only public GitHub repositories are supported.",
              field: "repository_url",
            },
          }),
          { status: 400, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    render(<Home />);

    fireEvent.change(screen.getByLabelText("Public GitHub repository URL"), {
      target: { value: "https://gitlab.com/example/project" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Repository analysis" }));

    const alert = await screen.findByRole("alert", {
      name: "Repository analysis failed",
    });
    expect(alert.textContent).toContain(
      "Only public GitHub repositories are supported.",
    );
  });

  it("asks a repository question and presents verified citations", async () => {
    const architecture = {
      repository: {
        id: "github.com/example/project",
        host: "github.com",
        owner: "example",
        name: "project",
        canonical_url: "https://github.com/example/project",
      },
      revision: "0123456789abcdef0123456789abcdef01234567",
      modules: [
        {
          path: "src/index.ts",
          language: "typescript",
          parse_status: "complete",
          symbols: [{ name: "run", kind: "function", line: 1 }],
        },
      ],
      relationships: [],
      limitations: [],
    };
    const citation = {
      path: "src/index.ts",
      start_line: 1,
      end_line: 1,
      symbol: "run",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(architecture), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            query: "Where is the run function?",
            status: "answered",
            facts: [
              {
                text: "Source symbol run is declared at src/index.ts:1.",
                basis: "verified_source",
                citations: [citation],
              },
            ],
            evidence: [
              {
                kind: "symbol",
                basis: "verified_source",
                citation,
                score: 2,
                matched_terms: ["function", "run"],
              },
            ],
            inference: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    fireEvent.change(screen.getByLabelText("Public GitHub repository URL"), {
      target: { value: "https://github.com/example/project" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Repository analysis" }));
    expect(await screen.findByText("Architecture ready")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Question"), {
      target: { value: "Where is the run function?" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Repository question" }));

    expect(await screen.findByText("Verified source answer")).toBeTruthy();
    expect(
      screen.getByText(
        "Source symbol run is declared at src/index.ts:1.",
      ),
    ).toBeTruthy();
    expect(screen.getByText("src/index.ts · L1")).toBeTruthy();
    expect(screen.getByText("No model inference used")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

});
