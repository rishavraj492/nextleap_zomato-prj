import { FormEvent, useEffect, useId, useRef, useState, type CSSProperties } from "react";
import type { Facets, RecommendationRequest } from "../api";

const DEFAULT_BUDGET = "medium";
const DEFAULT_MIN_RATING = 3.5;
const RATING_STEP = 0.5;
const PREFERENCES_MAX = 500;

const BUDGET_COPY: Record<string, string> = {
  low: "Low · under ₹500",
  medium: "Medium · ₹500–₹1,000",
  high: "High · above ₹1,000",
};

type PreferenceFormProps = {
  facets: Facets;
  pending: boolean;
  serverMessage: string;
  onEdit: () => void;
  onSubmit: (request: RecommendationRequest) => void;
};

export function PreferenceForm({
  facets,
  pending,
  serverMessage,
  onEdit,
  onSubmit,
}: PreferenceFormProps) {
  const [location, setLocation] = useState("");
  const [budget, setBudget] = useState(() => initialBudget(facets));
  const [cuisine, setCuisine] = useState("");
  const [minRating, setMinRating] = useState(() =>
    clampRating(DEFAULT_MIN_RATING, facets.ratingMin, facets.ratingMax),
  );
  const [preferences, setPreferences] = useState("");
  const [locationError, setLocationError] = useState("");

  useEffect(() => {
    setLocation((current) => (facets.locations.includes(current) ? current : ""));
    setBudget((current) =>
      facets.budgets.includes(current) ? current : initialBudget(facets),
    );
    setCuisine((current) => (facets.cuisines.includes(current) ? current : ""));
    setMinRating((current) => clampRating(current, facets.ratingMin, facets.ratingMax));
  }, [facets]);

  const locationMessage =
    locationError || (isLocationMessage(serverMessage) ? serverMessage : "");
  const formMessage = locationMessage ? "" : serverMessage;
  const span = facets.ratingMax - facets.ratingMin;
  const fill = span === 0 ? 0 : ((minRating - facets.ratingMin) / span) * 100;
  const midpoint = facets.ratingMin + span / 2;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;

    const chosenLocation = resolveLocation(facets.locations, location);
    setLocationError(chosenLocation ? "" : "Choose a neighborhood from the list.");
    if (!chosenLocation) return;

    const trimmedPreferences = preferences.trim();
    onSubmit({
      location: chosenLocation,
      budget,
      cuisines: cuisine ? [cuisine] : [],
      minRating,
      ...(trimmedPreferences ? { preferences: trimmedPreferences } : {}),
    });
  }

  return (
    <form className="preferences" onSubmit={handleSubmit} aria-busy={pending}>
      <LocationField
        locations={facets.locations}
        value={location}
        error={locationMessage}
        onChange={(next) => {
          setLocationError("");
          onEdit();
          setLocation(next);
        }}
      />

      <div>
        <span className="field-label" id="budget-label">
          Budget
        </span>
        <div className="budget" role="radiogroup" aria-labelledby="budget-label">
          {facets.budgets.map((option) => (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={budget === option}
              className="budget-option"
              onClick={() => {
                onEdit();
                setBudget(option);
              }}
            >
              {budgetLabel(option)}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="field-label" htmlFor="cuisine">
          Cuisine
        </label>
        <div className="control">
          <select
            id="cuisine"
            value={cuisine}
            onChange={(event) => {
              onEdit();
              setCuisine(event.target.value);
            }}
          >
            <option value="">Any cuisine</option>
            {facets.cuisines.map((token) => (
              <option key={token} value={token}>
                {titleCase(token)}
              </option>
            ))}
          </select>
          <span className="control-icon">
            <Chevron />
          </span>
        </div>
      </div>

      <div className="rating">
        <div className="rating-head">
          <label className="field-label" htmlFor="min-rating">
            Minimum rating
          </label>
          <span className="rating-value">
            <Star />
            {minRating.toFixed(1)}
          </span>
        </div>
        <input
          id="min-rating"
          className="rating-slider"
          type="range"
          min={facets.ratingMin}
          max={facets.ratingMax}
          step={RATING_STEP}
          value={minRating}
          style={{ "--fill": `${fill}%` } as CSSProperties}
          onChange={(event) => {
            onEdit();
            setMinRating(
              clampRating(Number(event.target.value), facets.ratingMin, facets.ratingMax),
            );
          }}
        />
        <div className="rating-scale">
          <span>{facets.ratingMin.toFixed(1)}</span>
          <span>{midpoint.toFixed(1)}</span>
          <span>{facets.ratingMax.toFixed(1)}</span>
        </div>
      </div>

      <div>
        <label className="field-label" htmlFor="preferences">
          Additional preferences
        </label>
        <textarea
          id="preferences"
          value={preferences}
          maxLength={PREFERENCES_MAX}
          rows={3}
          placeholder="Family-friendly, quick service, quiet room"
          onChange={(event) => {
            onEdit();
            setPreferences(event.target.value);
          }}
        />
        <p className="hint">
          {preferences.length} / {PREFERENCES_MAX}
        </p>
      </div>

      {formMessage ? (
        <p className="form-alert" role="alert">
          <ErrorIcon />
          {formMessage}
        </p>
      ) : null}

      <button className="submit" type="submit" disabled={pending}>
        {pending ? (
          <>
            <span className="spinner spinner-light" aria-hidden="true" />
            Finding restaurants…
          </>
        ) : (
          "Find restaurants"
        )}
      </button>
    </form>
  );
}

function LocationField({
  locations,
  value,
  error,
  onChange,
}: {
  locations: string[];
  value: string;
  error: string;
  onChange: (location: string) => void;
}) {
  const listId = useId();
  const errorId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  const query = value.trim();
  const matches = locations.filter((item) => item.toLowerCase().includes(query.toLowerCase()));
  const activeOption = matches[activeIndex] ?? matches[0];

  function commit(next: string) {
    onChange(next);
    setOpen(false);
  }

  return (
    <div className="location" ref={rootRef}>
      <label className="field-label" htmlFor="location">
        Neighborhood
      </label>
      <div className="control">
        <input
          id="location"
          type="text"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={listId}
          aria-activedescendant={open && activeOption ? optionId(listId, activeOption) : undefined}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          value={value}
          placeholder="Search neighborhoods"
          autoComplete="off"
          onChange={(event) => {
            onChange(event.target.value);
            setActiveIndex(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              if (!open) {
                setOpen(true);
                setActiveIndex(0);
              } else {
                setActiveIndex((index) => Math.min(index + 1, Math.max(matches.length - 1, 0)));
              }
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setOpen(true);
              setActiveIndex((index) => Math.max(index - 1, 0));
            } else if (event.key === "Enter" && open && activeOption) {
              event.preventDefault();
              commit(activeOption);
            } else if (event.key === "Escape") {
              setOpen(false);
            }
          }}
        />
        <span className="control-icon">
          <Chevron open={open} />
        </span>
        {open ? (
          <ul id={listId} role="listbox" className="location-list">
            {matches.length === 0 ? (
              <li className="location-empty">No matching neighborhoods</li>
            ) : (
              matches.map((item) => (
                <li key={item} role="presentation">
                  <button
                    id={optionId(listId, item)}
                    type="button"
                    role="option"
                    aria-selected={item === activeOption}
                    onMouseDown={(event) => event.preventDefault()}
                    onMouseEnter={() => setActiveIndex(matches.indexOf(item))}
                    onClick={() => commit(item)}
                  >
                    <span>{highlight(item, query)}</span>
                    {item === activeOption && query ? <span className="match-tag">Match</span> : null}
                  </button>
                </li>
              ))
            )}
          </ul>
        ) : null}
      </div>
      {error ? (
        <p id={errorId} className="field-error" role="alert">
          <ErrorIcon />
          {error}
        </p>
      ) : null}
    </div>
  );
}

function Chevron({ open = false }: { open?: boolean }) {
  return (
    <svg
      className={open ? "chevron-icon is-open" : "chevron-icon"}
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        d="M19 9l-7 7-7-7"
      />
    </svg>
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

function ErrorIcon() {
  return (
    <svg className="error-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path
        fill="currentColor"
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function highlight(text: string, query: string) {
  if (!query) return text;
  const index = text.toLowerCase().indexOf(query.toLowerCase());
  if (index < 0) return text;
  return (
    <>
      {text.slice(0, index)}
      <strong>{text.slice(index, index + query.length)}</strong>
      {text.slice(index + query.length)}
    </>
  );
}

function optionId(listId: string, location: string): string {
  const safeList = listId.replace(/[^a-zA-Z0-9_-]/g, "");
  const safeLocation = location.replace(/[^a-zA-Z0-9_-]/g, "");
  return `${safeList}-${safeLocation}`;
}

function resolveLocation(locations: string[], query: string): string | null {
  const typed = query.trim().toLowerCase();
  if (!typed) return null;
  return locations.find((item) => item.toLowerCase() === typed) ?? null;
}

function initialBudget(facets: Facets): string {
  if (facets.budgets.includes(DEFAULT_BUDGET)) return DEFAULT_BUDGET;
  return facets.budgets[0] ?? DEFAULT_BUDGET;
}

function clampRating(value: number, min: number, max: number): number {
  const stepped = Math.round(value / RATING_STEP) * RATING_STEP;
  return Math.min(max, Math.max(min, stepped));
}

function budgetLabel(value: string): string {
  return BUDGET_COPY[value] ?? titleCase(value);
}

function isLocationMessage(message: string): boolean {
  return /location|neighborhood/i.test(message);
}

function titleCase(value: string): string {
  return value
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
