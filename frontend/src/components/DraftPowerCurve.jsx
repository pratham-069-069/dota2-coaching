import React, { useMemo } from "react";

export default function DraftPowerCurve({ radiantPicks = [], direPicks = [], heroMap = {} }) {
  // Phase power calculation for Radiant & Dire
  const phases = ["Early (0-15m)", "Mid (15-30m)", "Late (30-45m)", "Ultra (45m+)"];

  const powerData = useMemo(() => {
    // Default baseline curves
    let radEarly = 50, radMid = 50, radLate = 50, radUltra = 50;
    let direEarly = 50, direMid = 50, direLate = 50, direUltra = 50;

    const evaluateTeam = (picks) => {
      let early = 50, mid = 50, late = 50, ultra = 50;
      picks.forEach((id) => {
        const hero = heroMap[id];
        const name = (hero?.name || "").toLowerCase();

        // Late game hyper-carries
        if (name.includes("anti-mage") || name.includes("phantom assassin") || name.includes("spectre") || name.includes("medusa") || name.includes("terrorblade") || name.includes("faceless")) {
          early -= 5;
          mid += 2;
          late += 8;
          ultra += 12;
        }
        // Early lane dominators & tempo
        else if (name.includes("axe") || name.includes("pudge") || name.includes("slardar") || name.includes("spirit breaker") || name.includes("undying") || name.includes("viper")) {
          early += 8;
          mid += 6;
          late -= 4;
          ultra -= 8;
        }
        // Mid-game flash farmers & pushers
        else if (name.includes("juggernaut") || name.includes("sven") || name.includes("lina") || name.includes("shadow fiend") || name.includes("leshrac")) {
          early += 3;
          mid += 8;
          late += 4;
          ultra -= 2;
        }
        // High-scaling casters
        else if (name.includes("invoker") || name.includes("storm") || name.includes("tinker") || name.includes("zeus")) {
          early -= 2;
          mid += 5;
          late += 7;
          ultra += 8;
        }
        // Early supports
        else {
          early += 4;
          mid += 2;
          late -= 2;
          ultra -= 4;
        }
      });
      return {
        early: Math.max(30, Math.min(80, early)),
        mid: Math.max(30, Math.min(80, mid)),
        late: Math.max(30, Math.min(80, late)),
        ultra: Math.max(30, Math.min(80, ultra)),
      };
    };

    const rad = evaluateTeam(radiantPicks);
    const dire = evaluateTeam(direPicks);

    return [
      { phase: "Early (0-15m)", rad: rad.early, dire: dire.early },
      { phase: "Mid (15-30m)", rad: rad.mid, dire: dire.mid },
      { phase: "Late (30-45m)", rad: rad.late, dire: dire.late },
      { phase: "Ultra (45m+)", rad: rad.ultra, dire: dire.ultra },
    ];
  }, [radiantPicks, direPicks, heroMap]);

  const chartW = 300;
  const chartH = 95;
  const padX = 35;
  const padY = 15;
  const plotW = chartW - padX * 2;
  const plotH = chartH - padY * 2;

  const radPoints = powerData.map((d, i) => {
    const x = padX + (i / (powerData.length - 1)) * plotW;
    const y = padY + (1 - (d.rad - 20) / 70) * plotH;
    return `${x},${y}`;
  }).join(" ");

  const direPoints = powerData.map((d, i) => {
    const x = padX + (i / (powerData.length - 1)) * plotW;
    const y = padY + (1 - (d.dire - 20) / 70) * plotH;
    return `${x},${y}`;
  }).join(" ");

  // Identify Win Condition
  const latestDiff = powerData[3].rad - powerData[3].dire;
  const midDiff = powerData[1].rad - powerData[1].dire;
  let winCondition = "Even scaling across both lineups";
  if (latestDiff >= 6) winCondition = "Radiant scales stronger into 40m+ late game";
  else if (latestDiff <= -6) winCondition = "Dire out-scales Radiant in ultra late game";
  else if (midDiff >= 5) winCondition = "Radiant mid-game power spike window (15-28m)";
  else if (midDiff <= -5) winCondition = "Dire mid-game power spike window (15-28m)";

  return (
    <div style={{
      width: "100%",
      marginTop: "12px",
      padding: "10px",
      background: "rgba(0, 0, 0, 0.25)",
      borderRadius: "var(--radius-sm)",
      border: "1px solid rgba(255, 255, 255, 0.05)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
        <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
          Draft Power Spike Trajectory
        </span>
        <div style={{ display: "flex", gap: "8px", fontSize: "0.68rem", fontFamily: "var(--font-mono)" }}>
          <span style={{ color: "var(--radiant-green)" }}>● Radiant</span>
          <span style={{ color: "var(--dire-crimson)" }}>● Dire</span>
        </div>
      </div>

      <svg viewBox={`0 0 ${chartW} ${chartH}`} style={{ width: "100%", height: "80px", display: "block" }}>
        {/* Baseline 50% line */}
        <line x1={padX} y1={chartH / 2} x2={chartW - padX} y2={chartH / 2} stroke="rgba(255, 255, 255, 0.1)" strokeDasharray="3 3" />

        {/* Radiant Curve */}
        <polyline points={radPoints} fill="none" stroke="var(--radiant-green)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Dire Curve */}
        <polyline points={direPoints} fill="none" stroke="var(--dire-crimson)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Data points */}
        {powerData.map((d, i) => {
          const x = padX + (i / (powerData.length - 1)) * plotW;
          const radY = padY + (1 - (d.rad - 20) / 70) * plotH;
          const direY = padY + (1 - (d.dire - 20) / 70) * plotH;
          return (
            <g key={i}>
              <circle cx={x} cy={radY} r="3" fill="#0f172a" stroke="var(--radiant-green)" strokeWidth="1.5" />
              <circle cx={x} cy={direY} r="3" fill="#0f172a" stroke="var(--dire-crimson)" strokeWidth="1.5" />
              <text x={x} y={chartH - 2} fill="var(--text-faint)" fontSize="8.5" textAnchor="middle" fontFamily="var(--font-mono)">
                {["0-15m", "15-30m", "30-45m", "45m+"][i]}
              </text>
            </g>
          );
        })}
      </svg>

      <div style={{ fontSize: "0.7rem", color: "var(--aegis-gold)", textAlign: "center", marginTop: "2px", fontStyle: "italic" }}>
        Coach Note: {winCondition}
      </div>
    </div>
  );
}
