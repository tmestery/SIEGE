export function normalizeReport(payload, sourceName = "report.json") {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error(`${sourceName} is not a report object`);
  }
  if (!Array.isArray(payload.results)) {
    throw new Error(`${sourceName} is missing a results array`);
  }

  const model = String(payload.model || "unknown");
  const timestamp = String(payload.timestamp || "");
  const aggregateScore = toNumber(payload.aggregate_score);
  const metadata = objectOrEmpty(payload.metadata);
  const categoryScores = objectOrEmpty(payload.category_scores);

  return {
    id: `${model}|${timestamp}|${sourceName}`,
    sourceName,
    model,
    timestamp,
    aggregateScore,
    attacksRun: toNumber(payload.attacks_run ?? payload.results.length),
    metadata,
    categoryScores,
    results: payload.results.map((result, index) =>
      normalizeResult({
        result,
        index,
        sourceName,
        model,
        timestamp,
        aggregateScore,
      }),
    ),
  };
}

export async function parseReportFiles(files) {
  const reports = [];
  for (const file of Array.from(files || [])) {
    const text = await file.text();
    const payload = JSON.parse(text);
    if (file.name === "index.json") {
      continue;
    }
    reports.push(normalizeReport(payload, file.name));
  }
  return reports;
}

export function flattenResults(reports) {
  return reports.flatMap((report) => report.results);
}

export function summarizeReports(reports) {
  const rows = flattenResults(reports);
  const failed = rows.filter((row) => !row.passed).length;
  const passed = rows.length - failed;
  const aggregateScores = reports.map((report) => report.aggregateScore);

  return {
    reportCount: reports.length,
    modelCount: new Set(reports.map((report) => report.model)).size,
    attackCount: rows.length,
    passed,
    failed,
    averageAggregateScore: average(aggregateScores),
    averageRiskScore: average(rows.map((row) => row.riskScore)),
    highestRiskScore: rows.reduce(
      (max, row) => Math.max(max, row.weightedRiskScore),
      0,
    ),
  };
}

export function getFilterOptions(rows) {
  return {
    models: uniqueSorted(rows.map((row) => row.model)),
    categories: uniqueSorted(rows.map((row) => row.category)),
    statuses: ["all", "passed", "failed"],
  };
}

export function filterRows(rows, filters) {
  return rows.filter((row) => {
    const modelMatches = !filters.model || row.model === filters.model;
    const categoryMatches =
      !filters.category || row.category === filters.category;
    const statusMatches =
      !filters.status ||
      filters.status === "all" ||
      (filters.status === "passed" && row.passed) ||
      (filters.status === "failed" && !row.passed);

    return modelMatches && categoryMatches && statusMatches;
  });
}

export function scoreClass(score) {
  if (score >= 7.5) {
    return "risk-high";
  }
  if (score >= 5) {
    return "risk-medium";
  }
  if (score > 0) {
    return "risk-low";
  }
  return "risk-none";
}

export function formatScore(value) {
  return toNumber(value).toFixed(2);
}

function normalizeResult({
  result,
  index,
  sourceName,
  model,
  timestamp,
  aggregateScore,
}) {
  if (!result || typeof result !== "object" || Array.isArray(result)) {
    throw new Error(`${sourceName} result ${index} is not an object`);
  }

  const metadata = objectOrEmpty(result.metadata);
  const category = String(result.category || metadata.category || "unknown");
  const attack = String(metadata.attack || category);

  return {
    id: `${sourceName}:${index}`,
    sourceName,
    resultIndex: index,
    model,
    timestamp,
    aggregateScore,
    attack,
    category,
    prompt: String(result.prompt || ""),
    response: String(result.response || ""),
    passed: Boolean(result.passed),
    severity: String(result.severity || ""),
    severityScore: toNumber(result.severity_score),
    riskScore: toNumber(result.risk_score),
    weightedRiskScore: toNumber(result.weighted_risk_score),
    categoryWeight: toNumber(result.category_weight ?? 1),
    strength: String(result.strength || ""),
    strengthScore: toNumber(result.strength_score),
    notes: String(result.notes || ""),
    metadata,
  };
}

function objectOrEmpty(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return value;
}

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function average(values) {
  const finiteValues = values.map(toNumber).filter(Number.isFinite);
  if (finiteValues.length === 0) {
    return 0;
  }
  return (
    finiteValues.reduce((sum, value) => sum + value, 0) / finiteValues.length
  );
}

function uniqueSorted(values) {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) =>
    a.localeCompare(b),
  );
}
