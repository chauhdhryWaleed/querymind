"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Tooltip,
  Legend,
  type ChartOptions,
} from "chart.js";
import { Bar, Line, Pie } from "react-chartjs-2";
import type { VisualizationHint } from "@/lib/types";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Tooltip,
  Legend,
);

// Vivid, theme-agnostic series colors (matches the cyan/teal app palette).
const COLORS = [
  "oklch(0.78 0.13 205)", // cyan/teal
  "oklch(0.75 0.14 160)", // green
  "oklch(0.8 0.14 78)", // amber
  "oklch(0.72 0.18 330)", // magenta
  "oklch(0.7 0.16 285)", // indigo
];
// Neutral grey for axes/legend that reads on both light and dark.
const CHROME = "rgba(130,130,140,0.9)";
const GRID = "rgba(130,130,140,0.15)";

type Resolved = { type: "bar" | "line" | "pie"; labelKey: string; valueKeys: string[] };

function isNumeric(v: unknown): boolean {
  if (typeof v === "number") return Number.isFinite(v);
  if (typeof v === "string" && v.trim() !== "") return !Number.isNaN(Number(v));
  return false;
}

function isNumericColumn(rows: Record<string, unknown>[], col: string): boolean {
  const sample = rows.slice(0, 20).map((r) => r[col]).filter((v) => v !== null && v !== undefined);
  return sample.length > 0 && sample.every(isNumeric);
}

/**
 * Decide whether (and how) to chart a result. Honors the server's hint, but
 * falls back to a client-side heuristic (a label column plus numeric measures)
 * so most aggregate results get a graph instead of just a table. Returns null
 * when nothing sensible can be drawn.
 */
export function resolveChart(
  hint: VisualizationHint | undefined,
  columns: string[],
  rows: Record<string, unknown>[],
): Resolved | null {
  if (!columns.length || !rows.length) return null;

  if (hint && (hint.chart === "bar" || hint.chart === "line" || hint.chart === "pie")) {
    const labelKey = hint.x ?? columns[0];
    const valueKeys = (hint.y?.length ? hint.y : [columns[1] ?? columns[0]]).filter(Boolean);
    if (valueKeys.length) return { type: hint.chart, labelKey, valueKeys };
  }

  const numeric = columns.filter((c) => isNumericColumn(rows, c));
  const nonNumeric = columns.filter((c) => !numeric.includes(c));

  if (numeric.length >= 1 && nonNumeric.length >= 1) {
    const valueKeys = numeric.slice(0, 3);
    const type: Resolved["type"] = rows.length <= 8 && valueKeys.length === 1 ? "pie" : "bar";
    return { type, labelKey: nonNumeric[0], valueKeys };
  }
  if (numeric.length >= 2) {
    return { type: "bar", labelKey: columns[0], valueKeys: numeric.slice(0, 3) };
  }
  return null;
}

const num = (v: unknown): number => {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
};

export function ChartView({
  hint,
  columns,
  rows,
}: {
  hint: VisualizationHint;
  columns: string[];
  rows: Record<string, unknown>[];
}) {
  const resolved = resolveChart(hint, columns, rows);
  if (!resolved) {
    return <p className="p-6 text-sm text-muted-foreground">No chart fits this result.</p>;
  }

  const { type, labelKey, valueKeys } = resolved;
  const labels = rows.map((r) => String(r[labelKey] ?? ""));

  const data =
    type === "pie"
      ? {
          labels,
          datasets: [
            {
              label: valueKeys[0],
              data: rows.map((r) => num(r[valueKeys[0]])),
              backgroundColor: COLORS,
              borderWidth: 0,
            },
          ],
        }
      : {
          labels,
          datasets: valueKeys.map((k, i) => ({
            label: k,
            data: rows.map((r) => num(r[k])),
            backgroundColor: COLORS[i % COLORS.length],
            borderColor: COLORS[i % COLORS.length],
            borderWidth: type === "line" ? 2 : 0,
            tension: 0.3,
            pointRadius: 2,
          })),
        };

  const base = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: type === "pie" || valueKeys.length > 1,
        labels: { color: CHROME, boxWidth: 12 },
      },
    },
  };
  const options: ChartOptions<"bar" | "line" | "pie"> =
    type === "pie"
      ? base
      : {
          ...base,
          scales: {
            x: { ticks: { color: CHROME, autoSkip: true, maxRotation: 0 }, grid: { color: GRID } },
            y: { ticks: { color: CHROME }, grid: { color: GRID } },
          },
        };

  return (
    <div className="h-72 p-4">
      {type === "bar" && <Bar data={data} options={options as ChartOptions<"bar">} />}
      {type === "line" && <Line data={data} options={options as ChartOptions<"line">} />}
      {type === "pie" && <Pie data={data} options={options as ChartOptions<"pie">} />}
    </div>
  );
}
