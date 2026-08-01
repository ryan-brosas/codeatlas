export type AdmissionCode = "busy" | "rate_limited" | "timed_out";

function boundedKey(value: string | null) {
  const normalized = value?.trim();
  return normalized ? normalized.slice(0, 128) : null;
}

export function clientKeyFromHeaders(
  forwardedFor: string | null,
  realIp: string | null,
) {
  const proxyAddress = forwardedFor?.split(",").at(-1) ?? null;
  return boundedKey(proxyAddress) ?? boundedKey(realIp) ?? "unknown";
}

export function repositoryRateKey(repositoryUrl: string) {
  return repositoryUrl
    .trim()
    .toLowerCase()
    .replace(/^https:\/\/www\.github\.com\//, "https://github.com/")
    .replace(/\/+$/, "")
    .replace(/\.git$/, "");
}

const messages: Record<AdmissionCode, string> = {
  busy: "The public demo is at capacity. Try again shortly.",
  rate_limited: "The public demo request limit was reached. Try again shortly.",
  timed_out: "Repository analysis timed out. Try a smaller repository.",
};

export class AdmissionError extends Error {
  constructor(readonly code: AdmissionCode) {
    super(messages[code]);
    this.name = "AdmissionError";
  }
}

type Window = { count: number; startedAt: number };
type AdmissionKeys = { clientKey: string; repositoryKey: string };
type AdmissionOptions = {
  clientLimit: number;
  repositoryLimit: number;
  windowMs: number;
  maxConcurrent: number;
  maxTrackedKeys: number;
  timeoutMs: number;
  now?: () => number;
};

export class RequestAdmission {
  private readonly windows = new Map<string, Window>();
  private readonly now: () => number;
  private active = 0;

  constructor(private readonly options: AdmissionOptions) {
    const limits = [
      options.clientLimit,
      options.repositoryLimit,
      options.windowMs,
      options.maxConcurrent,
      options.maxTrackedKeys,
      options.timeoutMs,
    ];
    if (limits.some((value) => !Number.isInteger(value) || value < 1)) {
      throw new Error("Admission limits must be positive integers.");
    }
    this.now = options.now ?? Date.now;
  }

  async run<T>(
    keys: AdmissionKeys,
    operation: (signal: AbortSignal) => Promise<T>,
  ): Promise<T> {
    const now = this.now();
    this.prune(now);
    this.consume(`client:${keys.clientKey}`, this.options.clientLimit, now);
    this.consume(
      `repository:${keys.repositoryKey}`,
      this.options.repositoryLimit,
      now,
    );
    if (this.active >= this.options.maxConcurrent) {
      throw new AdmissionError("busy");
    }

    this.active += 1;
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(new AdmissionError("timed_out")),
      this.options.timeoutMs,
    );
    try {
      return await operation(controller.signal);
    } finally {
      clearTimeout(timeout);
      this.active -= 1;
    }
  }

  private consume(key: string, limit: number, now: number) {
    const current = this.windows.get(key);
    if (current) {
      if (current.count >= limit) throw new AdmissionError("rate_limited");
      current.count += 1;
      return;
    }
    if (this.windows.size >= this.options.maxTrackedKeys) {
      throw new AdmissionError("busy");
    }
    this.windows.set(key, { count: 1, startedAt: now });
  }

  private prune(now: number) {
    for (const [key, window] of this.windows) {
      if (window.startedAt + this.options.windowMs <= now) {
        this.windows.delete(key);
      }
    }
  }
}
