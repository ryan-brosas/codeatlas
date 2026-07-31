"use client";

import { useState, type FormEvent } from "react";

type RequestResult<T> =
  | { kind: "success"; data: T }
  | { kind: "error"; message: string };

type RequestState<T> =
  | { kind: "idle" }
  | { kind: "submitting" }
  | RequestResult<T>;

export function useRepositoryRequest<T>(
  fieldName: string,
  request: (value: string) => Promise<RequestResult<T>>,
) {
  const [state, setState] = useState<RequestState<T>>({ kind: "idle" });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = new FormData(event.currentTarget).get(fieldName);
    if (typeof value !== "string" || !value.trim()) return;
    setState({ kind: "submitting" });
    setState(await request(value));
  }

  return { state, handleSubmit };
}
