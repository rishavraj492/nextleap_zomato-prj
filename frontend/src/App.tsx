import { useEffect, useState } from "react";
import {
  ApiError,
  fetchFacets,
  fetchRecommendations,
  type Facets,
  type RecommendationRequest,
  type RecommendationResponse,
} from "./api";
import { PreferenceForm } from "./components/PreferenceForm";
import { ResultSkeletons, Results } from "./components/Results";

export default function App() {
  const [facets, setFacets] = useState<Facets | null>(null);
  const [facetsError, setFacetsError] = useState(false);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [searchedLocation, setSearchedLocation] = useState("");
  const [serverMessage, setServerMessage] = useState("");
  const [requestFailed, setRequestFailed] = useState(false);
  const [lastRequest, setLastRequest] = useState<RecommendationRequest | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchFacets(controller.signal)
      .then((data) => {
        setFacets(data);
        setFacetsError(false);
      })
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        setFacetsError(true);
      });
    return () => controller.abort();
  }, []);

  async function handleSubmit(request: RecommendationRequest) {
    setLastRequest(request);
    setPending(true);
    setServerMessage("");
    setRequestFailed(false);
    try {
      const next = await fetchRecommendations(request);
      setResult(next);
      setSearchedLocation(request.location);
    } catch (error: unknown) {
      if (isAbortError(error)) return;
      if (error instanceof ApiError && error.status === 422) {
        setServerMessage(error.message);
        return;
      }
      setRequestFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="page">
      <header className="masthead">
        <div className="wordmark">
          <span>Table</span>
          <span className="wordmark-dot" aria-hidden="true" />
        </div>
        <p>AI picks for Bengaluru</p>
      </header>

      <section className="intro">
        <h1>Find a table that fits.</h1>
        <p>
          Choose a neighborhood, budget, and cuisine. We’ll rank a short list and explain why each
          place fits.
        </p>
      </section>

      {facets ? (
        <PreferenceForm
          facets={facets}
          pending={pending}
          serverMessage={serverMessage}
          onEdit={() => setServerMessage("")}
          onSubmit={handleSubmit}
        />
      ) : facetsError ? (
        <div className="notice notice-error" role="alert">
          <p className="notice-title">Restaurant options could not be loaded.</p>
          <p>Submit is absent. Please refresh or try again later.</p>
        </div>
      ) : (
        <div className="notice notice-loading" role="status">
          <span className="spinner" aria-hidden="true" />
          <p>Loading neighborhoods and cuisines…</p>
        </div>
      )}

      {requestFailed ? (
        <div className="request-error" role="alert">
          <span>Couldn’t reach the recommender. Try again.</span>
          <button type="button" onClick={() => lastRequest && void handleSubmit(lastRequest)} disabled={pending}>
            Retry
          </button>
        </div>
      ) : null}

      {pending ? <ResultSkeletons /> : null}
      {!pending && result ? <Results result={result} location={searchedLocation} /> : null}
    </div>
  );
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
