import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AdmissionError,
  clientKeyFromHeaders,
  repositoryRateKey,
  RequestAdmission,
} from "./request-admission";

const options = {
  clientLimit: 2,
  repositoryLimit: 2,
  windowMs: 1_000,
  maxConcurrent: 2,
  maxTrackedKeys: 10,
  timeoutMs: 5_000,
};

afterEach(() => {
  vi.useRealTimers();
});

describe("public request keys", () => {
  it("uses the proxy-appended client address instead of a spoofable first value", () => {
    expect(clientKeyFromHeaders("spoofed, 203.0.113.10", null)).toBe(
      "203.0.113.10",
    );
    expect(clientKeyFromHeaders(null, "203.0.113.11")).toBe("203.0.113.11");
    expect(clientKeyFromHeaders(null, null)).toBe("unknown");
  });

  it("normalizes equivalent repository rate keys", () => {
    expect(repositoryRateKey(" HTTPS://GitHub.com/Example/Project/ ")).toBe(
      "https://github.com/example/project",
    );
    expect(
      repositoryRateKey("https://www.github.com/Example/Project.git/"),
    ).toBe("https://github.com/example/project");
  });
});

describe("RequestAdmission", () => {
  it("limits requests by client and repository within a fixed window", async () => {
    let now = 0;
    const admission = new RequestAdmission({ ...options, now: () => now });
    const run = () =>
      admission.run(
        { clientKey: "client-a", repositoryKey: "github.com/example/project" },
        async () => "accepted",
      );

    await expect(run()).resolves.toBe("accepted");
    await expect(run()).resolves.toBe("accepted");
    await expect(run()).rejects.toMatchObject({ code: "rate_limited" });

    now = options.windowMs;
    await expect(run()).resolves.toBe("accepted");
  });

  it("caps concurrent analysis and releases capacity after completion", async () => {
    const admission = new RequestAdmission(options);
    let releaseFirst: () => void = () => undefined;
    let releaseSecond: () => void = () => undefined;
    const first = admission.run(
      { clientKey: "client-a", repositoryKey: "repository-a" },
      () => new Promise<void>((resolve) => (releaseFirst = resolve)),
    );
    const second = admission.run(
      { clientKey: "client-b", repositoryKey: "repository-b" },
      () => new Promise<void>((resolve) => (releaseSecond = resolve)),
    );

    await expect(
      admission.run(
        { clientKey: "client-c", repositoryKey: "repository-c" },
        async () => undefined,
      ),
    ).rejects.toMatchObject({ code: "busy" });

    releaseFirst();
    await first;
    await expect(
      admission.run(
        { clientKey: "client-c", repositoryKey: "repository-c" },
        async () => "accepted",
      ),
    ).resolves.toBe("accepted");
    releaseSecond();
    await second;
  });

  it("aborts requests that exceed the execution timeout", async () => {
    vi.useFakeTimers();
    const admission = new RequestAdmission({ ...options, timeoutMs: 50 });
    const result = admission.run(
      { clientKey: "client-a", repositoryKey: "repository-a" },
      (signal) =>
        new Promise<void>((_resolve, reject) => {
          signal.addEventListener("abort", () => reject(signal.reason));
        }),
    );

    const rejection = expect(result).rejects.toEqual(
      new AdmissionError("timed_out"),
    );
    await vi.advanceTimersByTimeAsync(50);
    await rejection;
  });

  it("bounds tracked rate-limit keys", async () => {
    const admission = new RequestAdmission({ ...options, maxTrackedKeys: 2 });
    await admission.run(
      { clientKey: "client-a", repositoryKey: "repository-a" },
      async () => undefined,
    );

    await expect(
      admission.run(
        { clientKey: "client-b", repositoryKey: "repository-b" },
        async () => undefined,
      ),
    ).rejects.toMatchObject({ code: "busy" });
  });
});
