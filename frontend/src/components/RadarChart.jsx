import React from "react";

export default function RadarChart({ data, size = 300, color = "#f5a623" }) {
  // data is an object like: { "Aggression": 68, "Farming Tempo": 78, "Objective Push": 65, "Team Utility": 62, "Survivability": 74, "Versatility": 85 }
  const entries = Object.entries(data);
  const numAxes = entries.length;
  if (numAxes < 3) return null;

  const cx = size / 2;
  const cy = size / 2;
  const radius = (size / 2) - 45; // margin for labels

  const levels = [20, 40, 60, 80, 100];

  // Helper to compute (x, y) for an axis index and a value (0 to 100)
  const getCoordinates = (index, value) => {
    const angle = (Math.PI * 2 / numAxes) * index - Math.PI / 2;
    const r = (value / 100) * radius;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  // Generate polygon points string for a given level
  const getLevelPolygonPath = (lvl) => {
    return Array.from({ length: numAxes })
      .map((_, i) => {
        const { x, y } = getCoordinates(i, lvl);
        return `${x},${y}`;
      })
      .join(" ");
  };

  // Polygon points for player's actual data
  const dataPoints = entries.map(([_, val], i) => getCoordinates(i, Math.max(10, Math.min(100, val))));
  const dataPolygonString = dataPoints.map((pt) => `${pt.x},${pt.y}`).join(" ");

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", position: "relative" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} size`} style={{ overflow: "visible" }}>
        <defs>
          <linearGradient id="radarFill" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.45" />
            <stop offset="100%" stopColor="#ff385c" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        {/* Concentric grid polygons */}
        {levels.map((lvl) => (
          <polygon
            key={lvl}
            points={getLevelPolygonPath(lvl)}
            fill="none"
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth="1"
            strokeDasharray={lvl === 100 ? "none" : "2,2"}
          />
        ))}

        {/* Spokes from center to vertices */}
        {entries.map(([label, _], i) => {
          const outer = getCoordinates(i, 100);
          return (
            <line
              key={label}
              x1={cx}
              y1={cy}
              x2={outer.x}
              y2={outer.y}
              stroke="rgba(255, 255, 255, 0.12)"
              strokeWidth="1"
            />
          );
        })}

        {/* Player Data Polygon */}
        <polygon
          points={dataPolygonString}
          fill="url(#radarFill)"
          stroke={color}
          strokeWidth="2.5"
          style={{ filter: `drop-shadow(0 0 8px ${color}88)` }}
        />

        {/* Data vertex dots */}
        {dataPoints.map((pt, i) => (
          <circle
            key={i}
            cx={pt.x}
            cy={pt.y}
            r="4"
            fill="#0f172a"
            stroke={color}
            strokeWidth="2"
          />
        ))}

        {/* Outer Axis Labels */}
        {entries.map(([label, val], i) => {
          const angle = (Math.PI * 2 / numAxes) * i - Math.PI / 2;
          const labelDist = radius + 22;
          const lx = cx + labelDist * Math.cos(angle);
          const ly = cy + labelDist * Math.sin(angle);

          const isTop = Math.abs(angle + Math.PI / 2) < 0.2;
          const isBottom = Math.abs(angle - Math.PI / 2) < 0.2;
          const textAnchor = isTop || isBottom ? "middle" : Math.cos(angle) > 0 ? "start" : "end";

          return (
            <text
              key={label}
              x={lx}
              y={ly}
              textAnchor={textAnchor}
              dominantBaseline="middle"
              fill="#cbd5e1"
              fontSize="11"
              fontWeight="600"
              fontFamily="var(--font-mono)"
            >
              {label} <tspan fill={color} fontWeight="700">({val})</tspan>
            </text>
          );
        })}
      </svg>
    </div>
  );
}
