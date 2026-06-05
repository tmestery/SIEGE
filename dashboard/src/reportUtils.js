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

export function normalizeDataset(payload, sourceName = "dataset.json") {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error(`${sourceName} is not a dataset object`);
  }
  if (!Array.isArray(payload.rows)) {
    throw new Error(`${sourceName} is missing a rows array`);
  }

  const datasetId = String(payload.dataset_id || sourceName);
  const title = String(payload.title || datasetId);
  const rows = payload.rows.map((row, index) =>
    normalizeDatasetRow({
      row,
      index,
      datasetId,
      sourceName,
    }),
  );

  return {
    id: datasetId,
    title,
    description: String(payload.description || ""),
    sourceName,
    summary: objectOrEmpty(payload.summary),
    sourceManifest: objectOrEmpty(payload.source_manifest),
    rows,
    reports: datasetRowsToReports(rows, title),
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

export function summarizeRows(rows) {
  const failed = rows.filter((row) => !row.passed).length;
  const passed = rows.length - failed;

  return {
    rowCount: rows.length,
    modelCount: new Set(rows.map((row) => row.model)).size,
    categoryCount: new Set(rows.map((row) => row.category)).size,
    attackCount: new Set(rows.map((row) => row.attack)).size,
    passed,
    failed,
    failureRate: rows.length === 0 ? 0 : failed / rows.length,
    averageRiskScore: average(rows.map((row) => row.riskScore)),
    averageWeightedRiskScore: average(rows.map((row) => row.weightedRiskScore)),
    highestRiskScore: rows.reduce(
      (max, row) => Math.max(max, row.weightedRiskScore),
      0,
    ),
  };
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
    attacks: uniqueSorted(rows.map((row) => row.attack)),
    categories: uniqueSorted(rows.map((row) => row.category)),
    statuses: ["all", "passed", "failed"],
  };
}

export function filterRows(rows, filters) {
  return rows.filter((row) => {
    const modelMatches = !filters.model || row.model === filters.model;
    const attackMatches = !filters.attack || row.attack === filters.attack;
    const categoryMatches =
      !filters.category || row.category === filters.category;
    const statusMatches =
      !filters.status ||
      filters.status === "all" ||
      (filters.status === "passed" && row.passed) ||
      (filters.status === "failed" && !row.passed);

    return modelMatches && attackMatches && categoryMatches && statusMatches;
  });
}

export function summarizeByModel(rows) {
  return summarizeGroups(rows, (row) => row.model).sort(
    (left, right) => right.averageWeightedRiskScore - left.averageWeightedRiskScore,
  );
}

export function summarizeByCategory(rows) {
  return summarizeGroups(rows, (row) => row.category).sort((left, right) =>
    left.label.localeCompare(right.label),
  );
}

export function buildRiskHeatmap(rows) {
  const models = uniqueSorted(rows.map((row) => row.model));
  const categories = uniqueSorted(rows.map((row) => row.category));
  const grouped = groupBy(rows, (row) => `${row.model}\u0000${row.category}`);

  return {
    models,
    categories,
    cells: models.flatMap((model) =>
      categories.map((category) => {
        const group = grouped.get(`${model}\u0000${category}`) || [];
        const failed = group.filter((row) => !row.passed).length;
        return {
          model,
          category,
          count: group.length,
          failed,
          failureRate: group.length === 0 ? 0 : failed / group.length,
          averageWeightedRiskScore: average(
            group.map((row) => row.weightedRiskScore),
          ),
        };
      }),
    ),
  };
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

export function formatPercent(value) {
  return `${Math.round(toNumber(value) * 100)}%`;
}

function normalizeDatasetRow({ row, index, datasetId, sourceName }) {
  if (!row || typeof row !== "object" || Array.isArray(row)) {
    throw new Error(`${sourceName} row ${index} is not an object`);
  }

  const metadata = objectOrEmpty(row.metadata);
  const category = String(row.category || metadata.category || "unknown");
  const attack = String(row.attack || metadata.attack || category);
  const model = String(row.model || "unknown");
  const reportPath = String(row.report_path || sourceName);
  const resultIndex = toNumber(row.result_index ?? index);

  return {
    id: `${datasetId}:${model}:${reportPath}:${resultIndex}`,
    sourceName,
    resultIndex,
    runId: String(row.run_id || datasetId),
    model,
    timestamp: String(row.timestamp || ""),
    aggregateScore: toNumber(row.aggregate_score),
    attack,
    category,
    prompt: String(row.prompt || ""),
    response: String(row.response || ""),
    passed: Boolean(row.passed),
    severity: String(row.severity || ""),
    severityScore: toNumber(row.severity_score),
    riskScore: toNumber(row.risk_score),
    weightedRiskScore: toNumber(row.weighted_risk_score ?? row.risk_score),
    categoryWeight: toNumber(row.category_weight ?? 1),
    strength: String(row.strength || ""),
    strengthScore: toNumber(row.strength_score),
    notes: String(row.notes || ""),
    metadata,
    reportMetadata: objectOrEmpty(row.report_metadata),
    reportPath,
  };
}

function datasetRowsToReports(rows, sourceName) {
  const grouped = groupBy(rows, (row) => row.model);
  return Array.from(grouped.entries())
    .map(([model, modelRows]) => ({
      id: `${sourceName}:${model}`,
      sourceName,
      model,
      timestamp: modelRows.find((row) => row.timestamp)?.timestamp || "",
      aggregateScore: average(modelRows.map((row) => row.aggregateScore)),
      attacksRun: modelRows.length,
      metadata: {
        dataset: sourceName,
      },
      categoryScores: categoryScoresForRows(modelRows),
      results: modelRows,
    }))
    .sort((left, right) => left.model.localeCompare(right.model));
}

function categoryScoresForRows(rows) {
  const grouped = groupBy(rows, (row) => row.category);
  return Object.fromEntries(
    Array.from(grouped.entries()).map(([category, categoryRows]) => {
      const failed = categoryRows.filter((row) => !row.passed).length;
      return [
        category,
        {
          score: average(categoryRows.map((row) => row.weightedRiskScore)),
          attacks_run: categoryRows.length,
          attacks_passed: categoryRows.length - failed,
          attacks_failed: failed,
        },
      ];
    }),
  );
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

function summarizeGroups(rows, getLabel) {
  return Array.from(groupBy(rows, getLabel).entries()).map(([label, group]) => {
    const failed = group.filter((row) => !row.passed).length;
    return {
      label,
      count: group.length,
      failed,
      passed: group.length - failed,
      failureRate: group.length === 0 ? 0 : failed / group.length,
      averageRiskScore: average(group.map((row) => row.riskScore)),
      averageWeightedRiskScore: average(group.map((row) => row.weightedRiskScore)),
      highestRiskScore: group.reduce(
        (max, row) => Math.max(max, row.weightedRiskScore),
        0,
      ),
    };
  });
}

function groupBy(values, getKey) {
  const grouped = new Map();
  for (const value of values) {
    const key = getKey(value);
    grouped.set(key, [...(grouped.get(key) || []), value]);
  }
  return grouped;
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
