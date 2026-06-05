import { useEffect, useMemo, useState } from "react";
import {
  buildRiskHeatmap,
  filterRows,
  flattenResults,
  formatPercent,
  formatScore,
  getFilterOptions,
  normalizeDataset,
  parseReportFiles,
  scoreClass,
  summarizeByCategory,
  summarizeByModel,
  summarizeReports,
  summarizeRows,
} from "./reportUtils.js";

const bundledDatasets = [
  {
    id: "local-ollama-sweep-2026-06-04",
    title: "Local Ollama Sweep 2026-06-04",
    path: "/datasets/local-ollama-sweep-2026-06-04.json",
  },
];

const initialFilters = {
  model: "",
  attack: "",
  category: "",
  status: "all",
};

const VIEW_MODES = {
  DATASET: "dataset",
  CUSTOM: "custom",
};

export default function App() {
  const [reports, setReports] = useState([]);
  const [dataset, setDataset] = useState(null);
  const [filters, setFilters] = useState(initialFilters);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [viewMode, setViewMode] = useState(VIEW_MODES.DATASET);

  const rows = useMemo(() => flattenResults(reports), [reports]);
  const summary = useMemo(() => summarizeReports(reports), [reports]);
  const rowSummary = useMemo(() => summarizeRows(rows), [rows]);
  const options = useMemo(() => getFilterOptions(rows), [rows]);
  const filteredRows = useMemo(
    () => filterRows(rows, filters),
    [rows, filters],
  );
  const modelRisk = useMemo(
    () => summarizeByModel(filteredRows),
    [filteredRows],
  );
  const categoryRisk = useMemo(
    () => summarizeByCategory(filteredRows),
    [filteredRows],
  );
  const heatmap = useMemo(() => buildRiskHeatmap(filteredRows), [filteredRows]);

  useEffect(() => {
    loadBundledDataset(bundledDatasets[0]);
  }, []);

  async function loadBundledDataset(datasetConfig) {
    setIsLoading(true);
    setError("");
    try {
      const response = await fetch(datasetConfig.path);
      if (!response.ok) {
        throw new Error(`Unable to load ${datasetConfig.title}`);
      }
      const payload = await response.json();
      const normalizedDataset = normalizeDataset(payload, datasetConfig.path);
      setDataset(normalizedDataset);
      setReports(normalizedDataset.reports);
      setFilters(initialFilters);
      setViewMode(VIEW_MODES.DATASET);
    } catch (loadError) {
      setError(loadError.message || "Unable to load bundled dataset.");
    } finally {
      setIsLoading(false);
    }
  }

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
      setDataset(null);
      setFilters(initialFilters);
      setViewMode(VIEW_MODES.CUSTOM);
    } catch (loadError) {
      setError(loadError.message || "Unable to load report files.");
    } finally {
      setIsLoading(false);
    }
  }

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function showDatasetView() {
    if (dataset) {
      setViewMode(VIEW_MODES.DATASET);
      return;
    }
    loadBundledDataset(bundledDatasets[0]);
  }

  function showCustomView() {
    setViewMode(VIEW_MODES.CUSTOM);
    setReports([]);
    setDataset(null);
    setFilters(initialFilters);
    setError("");
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">SEIGE Dashboard</p>
          <h1>React dataset dashboard for LLM security evaluations</h1>
          <p className="hero-copy">
            Explore the published SEIGE attack evaluation dataset with risk
            graphs, model/category heatmaps, filters, and attack-level
            evidence.
          </p>
        </div>
        <ViewSwitcher
          activeMode={viewMode}
          onCustom={showCustomView}
          onDataset={showDatasetView}
        />
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      {viewMode === VIEW_MODES.DATASET ? (
        <DatasetSelector
          activeDataset={dataset}
          datasets={bundledDatasets}
          isLoading={isLoading}
          onLoad={loadBundledDataset}
        />
      ) : (
        <CustomReportLoader isLoading={isLoading} onFiles={handleFiles} />
      )}

      <SummaryCards summary={summary} rowSummary={rowSummary} />

      {reports.length > 0 ? (
        <>
          <VisualInsights
            categoryRisk={categoryRisk}
            heatmap={heatmap}
            modelRisk={modelRisk}
          />
          <Filters
            filters={filters}
            options={options}
            onChange={updateFilter}
            shown={filteredRows.length}
            total={rows.length}
          />
          <ReportOverview reports={reports} />
          <ResultsTable rows={filteredRows} />
        </>
      ) : (
        <EmptyState />
      )}
    </main>
  );
}

function DatasetSelector({ activeDataset, datasets, isLoading, onLoad }) {
  return (
    <section className="panel dataset-panel">
      <div>
        <p className="eyebrow">Bundled dataset</p>
        <h2>{activeDataset?.title || "No bundled dataset loaded"}</h2>
        <p className="muted">
          {activeDataset?.description ||
            "Load the committed local Ollama sweep dataset or upload reports."}
        </p>
      </div>
      <div className="dataset-actions">
        {datasets.map((dataset) => (
          <button
            disabled={isLoading}
            key={dataset.id}
            onClick={() => onLoad(dataset)}
            type="button"
          >
            {isLoading ? "Loading..." : `Load ${dataset.title}`}
          </button>
        ))}
      </div>
    </section>
  );
}

function ViewSwitcher({ activeMode, onCustom, onDataset }) {
  return (
    <nav className="view-switcher" aria-label="Dashboard mode">
      <button
        className={activeMode === VIEW_MODES.DATASET ? "active" : ""}
        onClick={onDataset}
        type="button"
      >
        Published dataset
      </button>
      <button
        className={activeMode === VIEW_MODES.CUSTOM ? "active" : ""}
        onClick={onCustom}
        type="button"
      >
        Custom reports
      </button>
    </nav>
  );
}

function CustomReportLoader({ isLoading, onFiles }) {
  return (
    <section className="panel custom-report-panel">
      <div>
        <p className="eyebrow">Custom reports</p>
        <h2>Load your own SEIGE report JSON</h2>
        <p className="muted">
          Use this mode for local review, demos, or comparing a fresh run. The
          published dataset view is the default public dashboard.
        </p>
      </div>
      <label className="upload-card compact">
        <span>Load report JSON</span>
        <strong>{isLoading ? "Loading..." : "Choose files"}</strong>
        <input
          type="file"
          accept="application/json,.json"
          multiple
          onChange={onFiles}
        />
      </label>
    </section>
  );
}

function SummaryCards({ summary, rowSummary }) {
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
        label="Failure Rate"
        value={formatPercent(rowSummary.failureRate)}
        tone={rowSummary.failureRate >= 0.5 ? "bad" : "neutral"}
      />
      <MetricCard
        label="Highest Risk"
        value={formatScore(summary.highestRiskScore)}
        tone={summary.highestRiskScore >= 7.5 ? "bad" : "neutral"}
      />
    </section>
  );
}

function VisualInsights({ categoryRisk, heatmap, modelRisk }) {
  return (
    <section className="visual-grid" aria-label="Dataset visualizations">
      <BarChart
        title="Model risk ranking"
        eyebrow="Graph"
        rows={modelRisk.slice(0, 9)}
        valueKey="averageWeightedRiskScore"
        valueLabel={(row) => formatScore(row.averageWeightedRiskScore)}
        detailLabel={(row) =>
          `${row.failed}/${row.count} failed (${formatPercent(row.failureRate)})`
        }
      />
      <BarChart
        title="Category risk"
        eyebrow="Graph"
        rows={categoryRisk}
        valueKey="averageWeightedRiskScore"
        valueLabel={(row) => formatScore(row.averageWeightedRiskScore)}
        detailLabel={(row) =>
          `${row.failed}/${row.count} failed (${formatPercent(row.failureRate)})`
        }
      />
      <RiskHeatmap heatmap={heatmap} />
    </section>
  );
}

function BarChart({ detailLabel, eyebrow, rows, title, valueKey, valueLabel }) {
  const maxValue = Math.max(10, ...rows.map((row) => Number(row[valueKey] || 0)));

  return (
    <section className="panel chart-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
      </div>
      <div className="bar-list">
        {rows.map((row) => {
          const value = Number(row[valueKey] || 0);
          return (
            <div className="bar-row" key={row.label}>
              <div className="bar-label">
                <strong>{row.label}</strong>
                <span>{detailLabel(row)}</span>
              </div>
              <div className="bar-track" aria-hidden="true">
                <div
                  className={`bar-fill ${scoreClass(value)}`}
                  style={{ width: `${Math.max((value / maxValue) * 100, 2)}%` }}
                />
              </div>
              <span className={`score-pill ${scoreClass(value)}`}>
                {valueLabel(row)}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RiskHeatmap({ heatmap }) {
  return (
    <section className="panel heatmap-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Heatmap</p>
          <h2>Average weighted risk by model and category</h2>
        </div>
      </div>
      <div className="heatmap-wrap">
        <div
          className="heatmap-grid"
          style={{
            gridTemplateColumns: `minmax(230px, 1.3fr) repeat(${heatmap.categories.length}, minmax(150px, 1fr))`,
          }}
        >
          <div className="heatmap-corner">Model</div>
          {heatmap.categories.map((category) => (
            <div className="heatmap-header" key={category} title={category}>
              {displayLabel(category)}
            </div>
          ))}
          {heatmap.models.map((model) => (
            <HeatmapRow heatmap={heatmap} key={model} model={model} />
          ))}
        </div>
      </div>
    </section>
  );
}

function HeatmapRow({ heatmap, model }) {
  return (
    <>
      <div className="heatmap-model" title={model}>
        {displayLabel(model)}
      </div>
      {heatmap.categories.map((category) => {
        const cell = heatmap.cells.find(
          (candidate) =>
            candidate.model === model && candidate.category === category,
        );
        const score = Number(cell?.averageWeightedRiskScore || 0);
        return (
          <div
            className={`heatmap-cell ${scoreClass(score)}`}
            key={`${model}:${category}`}
            title={`${model} / ${category}: ${formatScore(score)} risk`}
          >
            <strong>{formatScore(score)}</strong>
            <span>
              {cell?.failed || 0}/{cell?.count || 0} failed
            </span>
          </div>
        );
      })}
    </>
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
        Attack
        <select
          value={filters.attack}
          onChange={(event) => onChange("attack", event.target.value)}
        >
          <option value="">All attacks</option>
          {options.attacks.map((attack) => (
            <option key={attack} value={attack}>
              {attack}
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
        Select the published dataset view or load SEIGE report JSON files in
        custom report mode. `index.json` files are ignored.
      </p>
    </section>
  );
}

function displayLabel(value) {
  return String(value || "unknown").replaceAll("_", " ");
}
