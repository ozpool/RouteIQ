import { env } from "../config/env";
import type { ApiErrorBody } from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function isErrorBody(body: unknown): body is ApiErrorBody {
  return typeof body === "object" && body !== null && "error" in body;
}

function flattenDetails(details: Record<string, unknown> | undefined): string {
  if (!details) return "";
  const messages: string[] = [];
  const walk = (value: unknown, path: string) => {
    if (Array.isArray(value) && value.every((v) => typeof v === "string")) {
      messages.push(`${path}: ${value.join(" ")}`);
    } else if (typeof value === "object" && value !== null) {
      for (const [key, inner] of Object.entries(value)) walk(inner, path ? `${path}.${key}` : key);
    }
  };
  walk(details, "");
  return messages.join(" · ");
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      ...init,
      headers: { Accept: "application/json", "Content-Type": "application/json", ...init?.headers },
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(0, "network", "Could not reach the RouteIQ server.");
  }

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (isErrorBody(body)) {
      const { code, message, details } = body.error;
      const detail = flattenDetails(details);
      throw new ApiError(response.status, code, detail ? `${message} ${detail}` : message, details);
    }
    throw new ApiError(response.status, "http", `Request failed (HTTP ${response.status}).`);
  }
  return body as T;
}
