import { useMemo, useState } from "react";
import {
  filterRows,
  flattenResults,
  formatScore,
  getFilterOptions,
  parseReportFiles,
  scoreClass,
  summarizeReports,
} from "./reportUtils.js";

const initialFilters = {
  model: "",
  category: "",
  status: "all",
};

export default function App() {
  const [reports, setReports] = useState([]);
  const [filters, setFilters] = useState(initialFilters);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const rows = useMemo(() => flattenResults(reports), [reports]);
  const summary = useMemo(() => summarizeReports(reports), [reports]);
  const options = useMemo(() => getFilterOptions(rows), [rows]);
  const filteredRows = useMemo(
    () => filterRows(rows, filters),
    [rows, filters],
  );

  async function handleFiles(event) {
    const files = event.target.files;
    if (!files || files.length === 0) {
      return;
    }

    setIsLoading(true);
    setError("");
    try {
      const parsedReports = await parseReportFiles(files);
      if (parsedReports.length === 0) {
        throw new Error("No report JSON files were loaded.");
      }
      setReports(parsedReports);
      setFilters(initialFilters);
    } catch (loadError) {
      setError(loadError.message || "Unable to load report files.");
    } finally {
      setIsLoading(false);
    }
  }

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">SEIGE Dashboard</p>
          <h1>React report dashboard for LLM security evaluations</h1>
          <p className="hero-copy">
            Load one or more SEIGE JSON reports to review aggregate risk,
            category scores, and attack-level evidence before sharing,
            publishing, or converting runs into datasets.
          </p>
        </div>
        <label className="upload-card">
          <span>Load report JSON</span>
          <strong>{isLoading ? "Loading..." : "Choose files"}</strong>
          <input
            type="file"
            accept="application/json,.json"
            multiple
            onChange={handleFiles}
          />
        </label>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <SummaryCards summary={summary} />

      {reports.length > 0 ? (
        <>
          <ReportOverview reports={reports} />
          <Filters
            filters={filters}
            options={options}
            onChange={updateFilter}
            shown={filteredRows.length}
            total={rows.length}
          />
          <ResultsTable rows={filteredRows} />
        </>
      ) : (
        <EmptyState />
      )}
    </main>
  );
}

function SummaryCards({ summary }) {
  return (
    <section className="metric-grid" aria-label="Evaluation summary">
      <MetricCard label="Reports" value={summary.reportCount} />
      <MetricCard label="Models" value={summary.modelCount} />
      <MetricCard label="Attack Rows" value={summary.attackCount} />
      <MetricCard label="Passed" value={summary.passed} tone="good" />
      <MetricCard label="Failed" value={summary.failed} tone="bad" />
      <MetricCard
        label="Avg Aggregate"
        value={formatScore(summary.averageAggregateScore)}
      />
      <MetricCard label="Avg Risk" value={formatScore(summary.averageRiskScore)} />
      <MetricCard
        label="Highest Risk"
        value={formatScore(summary.highestRiskScore)}
        tone={summary.highestRiskScore >= 7.5 ? "bad" : "neutral"}
      />
    </section>
  );
}

function MetricCard({ label, value, tone = "neutral" }) {
  return (
    <article className={`metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function ReportOverview({ reports }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Loaded reports</p>
          <h2>Model and category scores</h2>
        </div>
      </div>
      <div className="report-grid">
        {reports.map((report) => (
          <article className="report-card" key={report.id}>
            <div className="report-card-header">
              <div>
                <h3>{report.model}</h3>
                <p>{report.sourceName}</p>
              </div>
              <span className={`score-pill ${scoreClass(report.aggregateScore)}`}>
                {formatScore(report.aggregateScore)}
              </span>
            </div>
            <dl>
              <div>
                <dt>Timestamp</dt>
                <dd>{report.timestamp || "unknown"}</dd>
              </div>
              <div>
                <dt>Attacks run</dt>
                <dd>{report.attacksRun}</dd>
              </div>
            </dl>
            <CategoryScores categoryScores={report.categoryScores} />
          </article>
        ))}
      </div>
    </section>
  );
}

function CategoryScores({ categoryScores }) {
  const entries = Object.entries(categoryScores);
  if (entries.length === 0) {
    return <p className="muted">No category scores in this report.</p>;
  }

  return (
    <div className="category-list">
      {entries.map(([category, score]) => (
        <div className="category-row" key={category}>
          <span>{category}</span>
          <strong className={scoreClass(Number(score.score || 0))}>
            {formatScore(score.score)}
          </strong>
        </div>
      ))}
    </div>
  );
}

function Filters({ filters, options, onChange, shown, total }) {
  return (
    <section className="filters">
      <label>
        Model
        <select
          value={filters.model}
          onChange={(event) => onChange("model", event.target.value)}
        >
          <option value="">All models</option>
          {options.models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </label>
      <label>
        Category
        <select
          value={filters.category}
          onChange={(event) => onChange("category", event.target.value)}
        >
          <option value="">All categories</option>
          {options.categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </label>
      <label>
        Status
        <select
          value={filters.status}
          onChange={(event) => onChange("status", event.target.value)}
        >
          {options.statuses.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </label>
      <p>
        Showing <strong>{shown}</strong> of <strong>{total}</strong> attack rows
      </p>
    </section>
  );
}

function ResultsTable({ rows }) {
  if (rows.length === 0) {
    return (
      <section className="panel">
        <p className="muted">No attack rows match the selected filters.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Attack evidence</p>
          <h2>Results</h2>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Model</th>
              <th>Category</th>
              <th>Severity</th>
              <th>Risk</th>
              <th>Prompt</th>
              <th>Response</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.id}
                className={row.passed ? "row-passed" : "row-failed"}
              >
                <td>
                  <span className={`status-pill ${row.passed ? "pass" : "fail"}`}>
                    {row.passed ? "passed" : "failed"}
                  </span>
                </td>
                <td>{row.model}</td>
                <td>{row.category}</td>
                <td>{row.severity || "unknown"}</td>
                <td>
                  <span className={`score-pill ${scoreClass(row.weightedRiskScore)}`}>
                    {formatScore(row.weightedRiskScore)}
                  </span>
                </td>
                <td>
                  <TextBlock text={row.prompt} />
                </td>
                <td>
                  <TextBlock text={row.response} />
                </td>
                <td>
                  <TextBlock text={row.notes} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TextBlock({ text }) {
  return <pre>{text || "None"}</pre>;
}

function EmptyState() {
  return (
    <section className="empty-state">
      <h2>No reports loaded yet</h2>
      <p>
        Select SEIGE report JSON files from `examples/`, `artifacts/nightly-eval`,
        or a local Ollama run directory. `index.json` files are ignored.
      </p>
    </section>
  );
}
