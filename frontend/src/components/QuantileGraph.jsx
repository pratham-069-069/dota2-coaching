import React, { useState } from "react";

export default function QuantileGraph({ percentiles }) {
  const [hoveredMetric, setHoveredMetric] = useState(null);

  if (!percentiles || Object.keys(percentiles).length === 0) return null;

  const metricLabels = {
    gold_per_min: "GPM",
    xp_per_min: "XPM",
    hero_damage: "Hero Dmg",
    tower_damage: "Tower Dmg",
    last_hits: "Last Hits",
    denies: "Denies",
    stuns: "Stuns",
    survivability: "Survivability",
  };

  const metrics = Object.entries(percentiles).map(([key, value]) => ({
    key,
    label: metricLabels[key] || key.replace("_", " ").toUpperCase(),
    percentile: Math.max(1, Math.min(99, Number(value.toFixed(1)))),
  }));

  const chartW = 740;
  const chartH = 140;
  const padL = 30;
  const padR = 30;
  const padT = 30;
  const padB = 40;
  const plotW = chartW - padL - padR;

  // Background empirical Gaussian curve points
  const curvePoints = Array.from({ length: 41 }).map((_, i) => {
    const xPct = i / 40; // 0 to 1
    const x = padL + xPct * plotW;
    // Standard normal distribution shape centered at 0.5
    const z = (xPct - 0.5) * 4;
    const yVal = Math.exp(-0.5 * z * z);
    const y = chartH - padB - yVal * 65;
    return `${x},${y}`;
  });
  const curvePath = `M ${padL},${chartH - padB} L ${curvePoints.join(" L ")} L ${chartW - padR},${chartH - padB} Z`;

  return (
    <div style={{ position: "relative", width: "100%", background: "#0c111a", borderRadius: "6px", border: "1px solid var(--border-subtle)", padding: "12px", marginTop: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
        <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "#fff", textTransform: "uppercase" }}>
          Empirical Quantile Distribution (50,000 Matches Baseline)
        </div>
        <div style={{ display: "flex", gap: "12px", fontSize: "0.72rem", fontFamily: "var(--font-mono)" }}>
          <span style={{ color: "var(--dire-crimson)" }}>● &lt;25th (Deficit Zone)</span>
          <span style={{ color: "var(--aegis-gold)" }}>● 25th–75th (Median Norm)</span>
          <span style={{ color: "var(--radiant-green)" }}>● &gt;75th (Elite Tier)</span>
        </div>
      </div>

      <svg viewBox={`0 0 ${chartW} ${chartH}`} style={{ width: "100%", height: "130px", display: "block" }}>
        <defs>
          <linearGradient id="curveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ff3344" stopOpacity="0.25" />
            <stop offset="25%" stopColor="#ff3344" stopOpacity="0.15" />
            <stop offset="40%" stopColor="#f5a623" stopOpacity="0.25" />
            <stop offset="60%" stopColor="#f5a623" stopOpacity="0.25" />
            <stop offset="75%" stopColor="#00f59b" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#00f59b" stopOpacity="0.35" />
          </linearGradient>
        </defs>

        {/* Quantile Distribution Bell Curve */}
        <path d={curvePath} fill="url(#curveGrad)" stroke="rgba(255, 255, 255, 0.15)" strokeWidth="1.5" />

        {/* Reference Threshold Lines */}
        <line x1={padL + 0.25 * plotW} y1={padT} x2={padL + 0.25 * plotW} y2={chartH - padB} stroke="rgba(255, 51, 68, 0.4)" strokeDasharray="3 3" />
        <line x1={padL + 0.5 * plotW} y1={padT - 10} x2={padL + 0.5 * plotW} y2={chartH - padB} stroke="rgba(245, 166, 35, 0.6)" strokeWidth="1.5" />
        <line x1={padL + 0.75 * plotW} y1={padT} x2={padL + 0.75 * plotW} y2={chartH - padB} stroke="rgba(0, 245, 155, 0.4)" strokeDasharray="3 3" />

        {/* Axis Labels */}
        <text x={padL} y={chartH - padB + 16} fill="var(--text-faint)" fontSize="10" textAnchor="start" fontFamily="var(--font-mono)">P10 (Floor)</text>
        <text x={padL + 0.25 * plotW} y={chartH - padB + 16} fill="var(--dire-crimson)" fontSize="10" textAnchor="middle" fontFamily="var(--font-mono)">P25</text>
        <text x={padL + 0.5 * plotW} y={chartH - padB + 16} fill="var(--aegis-gold)" fontSize="10" textAnchor="middle" fontWeight="700" fontFamily="var(--font-mono)">P50 (Median)</text>
        <text x={padL + 0.75 * plotW} y={chartH - padB + 16} fill="var(--radiant-green)" fontSize="10" textAnchor="middle" fontFamily="var(--font-mono)">P75</text>
        <text x={chartW - padR} y={chartH - padB + 16} fill="var(--radiant-green)" fontSize="10" textAnchor="end" fontFamily="var(--font-mono)">P90 (Pro)</text>

        {/* Player Metric Pins */}
        {metrics.map((m, i) => {
          const x = padL + (m.percentile / 100) * plotW;
          const y = chartH - padB - 25 - (i % 3) * 16;
          const color = m.percentile >= 75 ? "var(--radiant-green)" : m.percentile >= 25 ? "var(--aegis-gold)" : "var(--dire-crimson)";

          return (
            <g
              key={m.key}
              onMouseEnter={() => setHoveredMetric(m)}
              onMouseLeave={() => setHoveredMetric(null)}
              style={{ cursor: "pointer" }}
            >
              {/* Drop line */}
              <line x1={x} y1={y} x2={x} y2={chartH - padB} stroke={color} strokeWidth="1" strokeDasharray="2 2" opacity="0.6" />
              {/* Pin circle */}
              <circle cx={x} cy={y} r="5" fill="#0c111a" stroke={color} strokeWidth="2.5" />
              {/* Metric Label */}
              <text x={x} y={y - 8} fill="#fff" fontSize="9.5" fontWeight="600" textAnchor="middle" fontFamily="var(--font-mono)">
                {m.label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Hover Tooltip */}
      {hoveredMetric && (
        <div
          className="chart-tooltip"
          style={{
            bottom: "4px",
            right: "12px",
          }}
        >
          <strong>{hoveredMetric.label}</strong>: Placed at the <strong style={{ color: hoveredMetric.percentile >= 75 ? "var(--radiant-green)" : hoveredMetric.percentile >= 25 ? "var(--aegis-gold)" : "var(--dire-crimson)" }}>
            {hoveredMetric.percentile}th percentile
          </strong> relative to all 50,000 matches.
        </div>
      )}
    </div>
  );
}
