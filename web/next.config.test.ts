import { expect, it } from "vitest";

import nextConfig from "./next.config";

it("adds security headers to every web response", async () => {
  const rules = await nextConfig.headers?.();
  const globalRule = rules?.find((rule) => rule.source === "/(.*)");
  const headers = Object.fromEntries(
    globalRule?.headers.map(({ key, value }) => [key, value]) ?? [],
  );

  expect(headers).toMatchObject({
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  });
});
