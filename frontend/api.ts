import type {
  ApiErrorBody,
  Commitment,
  CommitmentInput,
  User,
} from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Cannot reach StudyFlow right now. Check that the backend is running and try again.",
      0,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      body &&
      typeof body === "object" &&
      "error" in body &&
      typeof (body as ApiErrorBody).error === "string"
        ? (body as ApiErrorBody).error
        : `The request failed (${response.status}).`;
    throw new ApiError(message, response.status);
  }
  return body as T;
}

export async function getCurrentUser(): Promise<User> {
  const result = await request<{ user: User }>("/api/auth/me");
  return result.user;
}

export async function login(email: string, password: string): Promise<User> {
  const result = await request<{ user: User }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return result.user;
}

export function logout(): Promise<void> {
  return request<void>("/api/auth/logout", { method: "POST" });
}

export async function getCommitments(): Promise<Commitment[]> {
  const result = await request<{ commitments: Commitment[] }>("/api/commitments");
  return result.commitments;
}

export async function createCommitment(
  input: CommitmentInput,
): Promise<Commitment> {
  const result = await request<{ commitment: Commitment }>("/api/commitments", {
    method: "POST",
    body: JSON.stringify(input),
  });
  return result.commitment;
}

export async function updateCommitment(
  id: number,
  input: CommitmentInput,
): Promise<Commitment> {
  const result = await request<{ commitment: Commitment }>(
    `/api/commitments/${id}`,
    { method: "PATCH", body: JSON.stringify(input) },
  );
  return result.commitment;
}

export async function deleteCommitment(id: number): Promise<void> {
  return request<void>(`/api/commitments/${id}`, { method: "DELETE" });
}

export async function setCommitmentCompletion(
  id: number,
  completed: boolean,
): Promise<Commitment> {
  const result = await request<{ commitment: Commitment }>(
    `/api/commitments/${id}/completion`,
    { method: "PATCH", body: JSON.stringify({ completed }) },
  );
  return result.commitment;
}
