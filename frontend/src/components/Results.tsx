import type { Recommendation, RecommendationResponse } from "../api";

type ResultsProps = {
  result: RecommendationResponse;
  location: string;
};

export function Results({ result, location }: ResultsProps) {
  const cards = result.recommendations;
  const empty = cards.length === 0;

  return (
    <section className="results" aria-labelledby="results-heading" aria-live="polite">
      <div className="results-head">
        <h2 id="results-heading">Recommendations</h2>
        {cards.length > 0 ? <p className="meta-line">{matchLine(result.matchedCount, cards.length)}</p> : null}
        {!empty && result.summary ? <p className="summary">{result.summary}</p> : null}
      </div>

      {result.explanations === "unavailable" ? (
        <p className="sage-note">
          <span className="sage-dot" aria-hidden="true" />
          Written reasons are temporarily unavailable. Ratings, cost, and cuisine are still from the
          catalog.
        </p>
      ) : null}

      {empty ? (
        <div className="empty-panel">
          <p className="empty-title">Nothing in {location || "this neighborhood"} matched these filters.</p>
          <p className="empty-hint">Try a lower minimum rating or another budget.</p>
        </div>
      ) : (
        <ol className="cards">
          {cards.map((item, index) => (
            <RestaurantCard key={item.id} item={item} rank={index + 1} />
          ))}
        </ol>
      )}
    </section>
  );
}

export function ResultSkeletons() {
  return (
    <section className="results" aria-busy="true" aria-labelledby="results-heading">
      <div className="results-head">
        <h2 id="results-heading">Recommendations</h2>
      </div>
      <ol className="cards">
        {Array.from({ length: 5 }, (_, index) => (
          <li key={index} className="card card-skeleton" aria-hidden="true">
            <div className="bone bone-rank" />
            <div className="bone bone-title" />
            <div className="bone-row">
              <div className="bone bone-pill" />
              <div className="bone bone-pill" />
              <div className="bone bone-pill" />
            </div>
            <div className="bone bone-line" />
          </li>
        ))}
      </ol>
      <p className="sr-only">Finding restaurants…</p>
    </section>
  );
}

function RestaurantCard({ item, rank }: { item: Recommendation; rank: number }) {
  return (
    <li className="card">
      <span className="rank">#{rank}</span>
      <h3>{item.name}</h3>
      {item.cuisines ? <p className="cuisine">{item.cuisines}</p> : null}
      <div className="pills">
        <span className="pill">
          {item.rating !== null ? <Star /> : null}
          {formatRating(item.rating)}
        </span>
        <span className="pill">{formatCost(item.costForTwo)}</span>
        {item.location ? <span className="pill">{item.location}</span> : null}
        {item.restType ? <span className="pill">{item.restType}</span> : null}
      </div>
      {item.reason ? (
        <div className="why">
          <p className="why-label">Why this fits</p>
          <p className="why-copy">{item.reason}</p>
        </div>
      ) : null}
    </li>
  );
}

function Star() {
  return (
    <svg className="star" viewBox="0 0 20 20" aria-hidden="true">
      <path
        fill="currentColor"
        d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
      />
    </svg>
  );
}

function matchLine(matchedCount: number, shown: number): string {
  const matches = matchedCount === 1 ? "1 match" : `${matchedCount.toLocaleString("en-IN")} matches`;
  const top = shown === 1 ? "the top 1" : `the top ${shown}`;
  return `${matches} · showing ${top}`;
}

function formatRating(rating: number | null): string {
  return rating === null ? "No rating" : rating.toFixed(1);
}

function formatCost(costForTwo: number | null): string {
  if (costForTwo === null) return "Cost unavailable";
  return `₹${costForTwo.toLocaleString("en-IN")} for two`;
}
