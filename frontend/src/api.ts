const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type Facets = {
  locations: string[];
  cuisines: string[];
  budgets: string[];
  ratingMin: number;
  ratingMax: number;
};

export type RecommendationRequest = {
  location: string;
  budget: string;
  cuisines: string[];
  minRating: number;
  preferences?: string;
};

export type Recommendation = {
  id: string;
  name: string;
  cuisines: string;
  location: string;
  rating: number | null;
  votes: number;
  costForTwo: number | null;
  restType: string;
  reason: string | null;
};

export type RecommendationResponse = {
  summary: string;
  explanations: "available" | "unavailable" | "skipped";
  matchedCount: number;
  recommendations: Recommendation[];
};

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function fetchFacets(signal?: AbortSignal): Promise<Facets> {
  return request<Facets>("/api/facets", { signal });
}

export function fetchRecommendations(
  body: RecommendationRequest,
  signal?: AbortSignal,
): Promise<RecommendationResponse> {
  return request<RecommendationResponse>("/api/recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }
  return response.json() as Promise<T>;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string" && detail.trim()) return detail;
      if (Array.isArray(detail)) {
        const messages = detail
          .map((item) => {
            if (typeof item === "object" && item !== null && "msg" in item) {
              const message = (item as { msg: unknown }).msg;
              return typeof message === "string" ? message : "";
            }
            return "";
          })
          .filter(Boolean);
        if (messages.length > 0) return messages.join(" ");
      }
    }
  } catch {
    return `Request failed with status ${response.status}`;
  }
  return `Request failed with status ${response.status}`;
}
