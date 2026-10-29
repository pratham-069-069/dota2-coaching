import React, { useState, useEffect, useMemo } from "react";
import {
  Play, Pause, RotateCcw, Shield, Swords, Flame, Skull,
  Target, Award, AlertTriangle, CheckCircle, Clock, Zap,
  TrendingUp, Compass, Copy, Check, Radio, ChevronRight
} from "lucide-react";

export default function LiveSimulator({ heroes }) {
  // Game Clock
  const [isPlaying, setIsPlaying] = useState(false);
  const [gameSeconds, setGameSeconds] = useState(1350); // 22:30 default
  const [speed, setSpeed] = useState(1);

  // Live Game State
  const [radiantKills, setRadiantKills] = useState(18);
  const [direKills, setDireKills] = useState(14);
  const [netWorthLead, setNetWorthLead] = useState(4800); // positive = radiant lead, negative = dire
  
  // Roshan & Aegis state
  const [roshanState, setRoshanState] = useState("aegis_radiant"); // "alive", "dead", "aegis_radiant", "aegis_dire"
  const [aegisSecondsLeft, setAegisSecondsLeft] = useState(195); // 3m 15s

  // Towers standing (true = standing, false = destroyed)
  const [towers, setTowers] = useState({
    radiant: { t1_top: false, t2_top: true, t3_top: true, t1_mid: true, t2_mid: true, t3_mid: true, t1_bot: true, t2_bot: true, t3_bot: true, rax: 6 },
    dire: { t1_top: false, t2_top: false, t3_top: true, t1_mid: false, t2_mid: true, t3_mid: true, t1_bot: true, t2_bot: true, t3_bot: true, rax: 6 },
  });

  // Timeline events history for graph
  const [timelineEvents, setTimelineEvents] = useState([
    { minute: 0, radWinProb: 52.0, event: "Draft Completed (Radiant Slight Edge)", nwLead: 0, type: "draft" },
    { minute: 4, radWinProb: 55.5, event: "First Blood (Anti-Mage kill on Pudge)", nwLead: 650, type: "kill" },
    { minute: 9, radWinProb: 53.0, event: "Dire 3-man gank top lane", nwLead: 150, type: "kill" },
    { minute: 14, radWinProb: 58.2, event: "Dire Tier 1 Mid Tower Destroyed", nwLead: 2400, type: "tower" },
    { minute: 18, radWinProb: 63.5, event: "Radiant Claims Roshan & Aegis of the Immortal", nwLead: 3900, type: "roshan" },
    { minute: 22, radWinProb: 67.8, event: "Dire Tier 2 Top Crumbles to Split Push", nwLead: 4800, type: "tower" },
  ]);

  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [copiedBriefing, setCopiedBriefing] = useState(false);

  // Ticking live clock when playing
  useEffect(() => {
    let interval = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setGameSeconds((prev) => {
          const next = prev + 5 * speed;
          if (next > 3600) {
            setIsPlaying(false);
            return 3600;
          }
          return next;
        });
        if (aegisSecondsLeft > 0) {
          setAegisSecondsLeft((prev) => Math.max(0, prev - 5 * speed));
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, speed, aegisSecondsLeft]);

  const currentMinute = Math.floor(gameSeconds / 60);
  const currentSeconds = Math.floor(gameSeconds % 60);
  const formattedTime = `${String(currentMinute).padStart(2, "0")}:${String(currentSeconds).padStart(2, "0")}`;

  // Game Phase
  const gamePhase = useMemo(() => {
    if (currentMinute < 12) return { name: "Laning Phase & Rune Control", color: "var(--mana-blue)" };
    if (currentMinute < 26) return { name: "Mid-Game Tempo & Item Spikes", color: "var(--aegis-gold)" };
    if (currentMinute < 42) return { name: "Roshan Control & High-Ground Sieges", color: "var(--mystic-purple)" };
    return { name: "Ultra Late-Game Buyback Warfare", color: "var(--dire-crimson)" };
  }, [currentMinute]);

  // Dynamic Live Win Probability Calculation
  // Factors: Base draft (52%), Net Worth Lead (+- per 1k), Tower count diff, Aegis status, Time scaling
  const liveWinProb = useMemo(() => {
    let prob = 52.0; // base draft edge

    // Net worth impact (scales with game time)
    const nwScale = currentMinute < 15 ? 1.6 : currentMinute < 30 ? 1.1 : 0.7;
    prob += (netWorthLead / 1000) * nwScale;

    // Tower difference
    const radTowersDown = Object.values(towers.radiant).filter((t) => t === false).length;
    const direTowersDown = Object.values(towers.dire).filter((t) => t === false).length;
    prob += (direTowersDown - radTowersDown) * 2.8;

    // Aegis impact
    if (roshanState === "aegis_radiant" && aegisSecondsLeft > 0) prob += 5.5;
    if (roshanState === "aegis_dire" && aegisSecondsLeft > 0) prob -= 5.5;

    // Kill difference
    prob += (radiantKills - direKills) * 0.4;

    return Math.max(5.0, Math.min(95.0, Number(prob.toFixed(1))));
  }, [netWorthLead, towers, roshanState, aegisSecondsLeft, radiantKills, direKills, currentMinute]);

  // Map control calculation
  const mapControl = useMemo(() => {
    const radStanding = Object.values(towers.radiant).filter((t) => t === true).length;
    const direStanding = Object.values(towers.dire).filter((t) => t === true).length;
    const total = radStanding + direStanding || 1;
    const pct = Math.round((radStanding / total) * 100);
    return Math.max(15, Math.min(85, pct));
  }, [towers]);

  // Add an in-game event to the timeline
  const triggerEvent = (name, nwDelta, probDelta, type) => {
    const newNW = netWorthLead + nwDelta;
    setNetWorthLead(newNW);

    if (type === "kill_radiant") setRadiantKills((k) => k + 1);
    if (type === "kill_dire") setDireKills((k) => k + 1);
    if (type === "teamwipe_radiant") setRadiantKills((k) => k + 4);
    if (type === "teamwipe_dire") setDireKills((k) => k + 4);

    if (type === "roshan_radiant") {
      setRoshanState("aegis_radiant");
      setAegisSecondsLeft(300);
    } else if (type === "roshan_dire") {
      setRoshanState("aegis_dire");
      setAegisSecondsLeft(300);
    }

    const newPoint = {
      minute: currentMinute,
      radWinProb: Math.max(5, Math.min(95, Number((liveWinProb + probDelta).toFixed(1)))),
      event: name,
      nwLead: newNW,
      type: type.includes("roshan") ? "roshan" : type.includes("tower") ? "tower" : "kill",
    };

    setTimelineEvents((prev) => [...prev, newPoint]);
  };

  // Scenario Presets
  const loadScenario = (scenario) => {
    if (scenario === "laning") {
      setGameSeconds(600); // 10:00
      setNetWorthLead(850);
      setRadiantKills(7);
      setDireKills(6);
      setRoshanState("alive");
      setAegisSecondsLeft(0);
      setTowers({
        radiant: { t1_top: true, t2_top: true, t3_top: true, t1_mid: true, t2_mid: true, t3_mid: true, t1_bot: true, t2_bot: true, t3_bot: true, rax: 6 },
        dire: { t1_top: true, t2_top: true, t3_top: true, t1_mid: true, t2_mid: true, t3_mid: true, t1_bot: true, t2_bot: true, t3_bot: true, rax: 6 },
      });
      setTimelineEvents([
        { minute: 0, radWinProb: 52.0, event: "Draft Complete", nwLead: 0, type: "draft" },
        { minute: 4, radWinProb: 54.0, event: "First Blood Secured", nwLead: 400, type: "kill" },
        { minute: 10, radWinProb: 53.5, event: "Laning Phase Concluded", nwLead: 850, type: "event" },
      ]);
    } else if (scenario === "mid_push") {
      setGameSeconds(1440); // 24:00
      setNetWorthLead(6800);
      setRadiantKills(22);
      setDireKills(13);
      setRoshanState("aegis_radiant");
      setAegisSecondsLeft(210);
      setTowers({
        radiant: { t1_top: false, t2_top: true, t3_top: true, t1_mid: true, t2_mid: true, t3_mid: true, t1_bot: true, t2_bot: true, t3_bot: true, rax: 6 },
        dire: { t1_top: false, t2_top: false, t3_top: true, t1_mid: false, t2_mid: false, t3_mid: true, t1_bot: false, t2_bot: true, t3_bot: true, rax: 6 },
      });
      setTimelineEvents([
        { minute: 0, radWinProb: 52.0, event: "Draft Complete", nwLead: 0, type: "draft" },
        { minute: 12, radWinProb: 56.0, event: "Battle Fury Completed on AM", nwLead: 2100, type: "item" },
        { minute: 19, radWinProb: 65.0, event: "Roshan Slain + Aegis to Carry", nwLead: 5200, type: "roshan" },
        { minute: 24, radWinProb: 74.2, event: "High Ground Perimeter Breach", nwLead: 6800, type: "tower" },
      ]);
    } else if (scenario === "comeback") {
      setGameSeconds(2100); // 35:00
      setNetWorthLead(-7500); // Dire in lead
      setRadiantKills(24);
      setDireKills(31);
      setRoshanState("aegis_dire");
      setAegisSecondsLeft(140);
      setTowers({
        radiant: { t1_top: false, t2_top: false, t3_top: false, t1_mid: false, t2_mid: false, t3_mid: true, t1_bot: false, t2_bot: true, t3_bot: true, rax: 4 },
        dire: { t1_top: false, t2_top: true, t3_top: true, t1_mid: false, t2_mid: true, t3_mid: true, t1_bot: false, t2_bot: true, t3_bot: true, rax: 6 },
      });
      setTimelineEvents([
        { minute: 0, radWinProb: 52.0, event: "Draft Complete", nwLead: 0, type: "draft" },
        { minute: 18, radWinProb: 60.0, event: "Radiant Early Pressure", nwLead: 3000, type: "tower" },
        { minute: 28, radWinProb: 44.0, event: "Dire Wipe Teamfight & Counter-Push", nwLead: -3500, type: "kill" },
        { minute: 35, radWinProb: 28.5, event: "Dire Claims Aegis & Top Rax", nwLead: -7500, type: "roshan" },
      ]);
    }
  };

  // Live Strategic Coaching Directives
  const coachDirectives = useMemo(() => {
    const list = [];
    if (roshanState === "aegis_radiant" && aegisSecondsLeft > 0) {
      list.push({
        type: "aggressive",
        title: "Aegis Siege Window Active",
        text: `Aegis has ${Math.floor(aegisSecondsLeft / 60)}m ${aegisSecondsLeft % 60}s remaining. Group as 5 immediately to force tier 3 tower or barracks. Avoid passive jungle farming.`,
      });
    } else if (roshanState === "aegis_dire" && aegisSecondsLeft > 0) {
      list.push({
        type: "defensive",
        title: "Enemy Aegis Threat Active",
        text: `Dire carries Aegis (${Math.floor(aegisSecondsLeft / 60)}m left). Turtles inside base perimeter. Do not take skirmishes outside high-ground vision.`,
      });
    }

    if (netWorthLead > 6000) {
      list.push({
        type: "tempo",
        title: "Dominant Gold Advantage (+ " + netWorthLead.toLocaleString() + "g)",
        text: "Starve enemy map vision. Ward enemy jungle quadrants and choke points. Ensure buyback gold is banked on core heroes before initiating next 5v5.",
      });
    } else if (netWorthLead < -5000) {
      list.push({
        type: "comeback",
        title: "Deficit Defense Strategy (- " + Math.abs(netWorthLead).toLocaleString() + "g)",
        text: "Play around vision traps and smoke of deceit. Prioritize wave-cutting behind enemy pushes to delay high ground sieges until key defensive items (Force Staff, BKB) finish.",
      });
    } else {
      list.push({
        type: "neutral",
        title: "Tight Economic Equilibrium",
        text: "Gold advantage is within striking distance. Secure next Roshan timing and prioritize vision around river runes.",
      });
    }

    if (currentMinute >= 30) {
      list.push({
        type: "macro",
        title: "Late Game Buyback Discipline",
        text: "A death without buyback after 35 minutes directly risks the Ancient. Never commit to non-essential ganks without buyback reserve.",
      });
    }

    return list;
  }, [netWorthLead, roshanState, aegisSecondsLeft, currentMinute]);

  const copyBriefing = () => {
    const lines = [
      "========================================",
      `🔴 AEGIS LIVE MATCH STATE AUDIT // TIME: ${formattedTime}`,
      "========================================",
      `LIVE WIN PROBABILITY: Radiant ${liveWinProb}% vs Dire ${(100 - liveWinProb).toFixed(1)}%`,
      `NET WORTH SPREAD: ${netWorthLead >= 0 ? "+" + netWorthLead + "g (Radiant Lead)" : netWorthLead + "g (Dire Lead)"}`,
      `SCORE PACE: Radiant ${radiantKills} - ${direKills} Dire`,
      `MAP CONTROL: Radiant ${mapControl}% vs Dire ${100 - mapControl}%`,
      `ROSHAN & AEGIS: ${roshanState === "aegis_radiant" ? `Radiant Holds Aegis (${aegisSecondsLeft}s left)` : roshanState === "aegis_dire" ? `Dire Holds Aegis (${aegisSecondsLeft}s left)` : roshanState.toUpperCase()}`,
      "",
      "LIVE COACHING DIRECTIVES:",
      ...coachDirectives.map((d) => `  • [${d.title}] ${d.text}`),
      "========================================",
      "Generated by Aegis Coaching Intelligence Platform",
    ];

    navigator.clipboard.writeText(lines.join("\n"));
    setCopiedBriefing(true);
    setTimeout(() => setCopiedBriefing(false), 2500);
  };

  // SVG Chart Dimensions
  const chartW = 780;
  const chartH = 220;
  const padL = 45;
  const padR = 25;
  const padT = 20;
  const padB = 30;

  // Compute SVG Points for the Timeline Graph
  const chartPoints = useMemo(() => {
    const maxMin = Math.max(currentMinute, 40);
    return timelineEvents.map((pt) => {
      const x = padL + (pt.minute / maxMin) * (chartW - padL - padR);
      // y: 100% at padT, 50% at mid, 0% at chartH - padB
      const y = padT + (1 - pt.radWinProb / 100) * (chartH - padT - padB);
      return { ...pt, x, y };
    });
  }, [timelineEvents, currentMinute]);

  const svgPathD = useMemo(() => {
    if (chartPoints.length === 0) return "";
    return chartPoints.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "");
  }, [chartPoints]);

  const midY = padT + 0.5 * (chartH - padT - padB);

  return (
    <div style={{ padding: "1.5rem 0", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Top Match HUD Bar */}
      <div className="glass-panel" style={{
        padding: "1.2rem 2rem",
        marginBottom: "1.5rem",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderTop: "3px solid var(--aegis-gold)",
        position: "relative",
      }}>
        {/* Radiant Side Score */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "12px",
            height: "12px",
            borderRadius: "50%",
            background: "var(--radiant-green)",
            boxShadow: "0 0 12px var(--radiant-green)",
          }} />
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--radiant-green)", fontWeight: 700, letterSpacing: "0.08em" }}>
              THE RADIANT
            </div>
            <div className="font-stats" style={{ fontSize: "1.8rem", color: "#fff", lineHeight: 1 }}>
              {radiantKills} <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>KILLS</span>
            </div>
          </div>
        </div>

        {/* Center Live Game Clock & Win Rate HUD */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span className="live-indicator-dot" />
            <span className="badge badge-live" style={{ fontSize: "0.72rem" }}>LIVE SIMULATION</span>
            <span style={{ fontSize: "0.8rem", color: gamePhase.color, fontWeight: 700, fontFamily: "var(--font-mono)" }}>
              {gamePhase.name}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "16px", margin: "4px 0" }}>
            <div className="font-stats" style={{ fontSize: "2.4rem", color: "var(--aegis-gold)", letterSpacing: "0.05em" }}>
              {formattedTime}
            </div>
            <div style={{ display: "flex", gap: "4px" }}>
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                style={{
                  background: isPlaying ? "rgba(239, 68, 68, 0.2)" : "rgba(0, 245, 155, 0.2)",
                  border: `1px solid ${isPlaying ? "#ef4444" : "var(--radiant-green)"}`,
                  color: isPlaying ? "#f87171" : "var(--radiant-green)",
                  borderRadius: "4px",
                  padding: "6px 10px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "0.8rem",
                  fontWeight: 700,
                }}
              >
                {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                {isPlaying ? "Pause" : "Play Sim"}
              </button>
              <button
                onClick={() => setSpeed(speed === 1 ? 2 : speed === 2 ? 4 : 1)}
                style={{
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-muted)",
                  borderRadius: "4px",
                  padding: "6px 8px",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {speed}x
              </button>
            </div>
          </div>

          {/* Probability Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", width: "280px" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--radiant-green)", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
              {liveWinProb}%
            </span>
            <div style={{ flex: 1, height: "8px", borderRadius: "4px", background: "#1a2232", overflow: "hidden", display: "flex" }}>
              <div style={{
                width: `${liveWinProb}%`,
                background: "linear-gradient(90deg, #00f59b 0%, #00d084 100%)",
                transition: "width 0.3s ease",
              }} />
              <div style={{
                width: `${100 - liveWinProb}%`,
                background: "linear-gradient(90deg, #ff4d5a 0%, #ff3344 100%)",
                transition: "width 0.3s ease",
              }} />
            </div>
            <span style={{ fontSize: "0.8rem", color: "var(--dire-crimson)", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
              {(100 - liveWinProb).toFixed(1)}%
            </span>
          </div>

          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            Net Worth: <strong style={{ color: netWorthLead >= 0 ? "var(--radiant-green)" : "var(--dire-crimson)" }}>
              {netWorthLead >= 0 ? `+${netWorthLead.toLocaleString()}g Radiant` : `+${Math.abs(netWorthLead).toLocaleString()}g Dire`}
            </strong>
          </div>
        </div>

        {/* Dire Side Score */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px", textAlign: "right" }}>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--dire-crimson)", fontWeight: 700, letterSpacing: "0.08em" }}>
              THE DIRE
            </div>
            <div className="font-stats" style={{ fontSize: "1.8rem", color: "#fff", lineHeight: 1 }}>
              {direKills} <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>KILLS</span>
            </div>
          </div>
          <div style={{
            width: "12px",
            height: "12px",
            borderRadius: "50%",
            background: "var(--dire-crimson)",
            boxShadow: "0 0 12px var(--dire-crimson)",
          }} />
        </div>
      </div>

      {/* Main Grid: Left Graphs, Right Live Controls & Directives */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 420px", gap: "1.5rem", marginBottom: "1.5rem" }}>
        {/* Left Column: Interactive Graphs */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Graph 1: Live Win Probability Swing Timeline */}
          <div className="glass-panel" style={{ padding: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <div>
                <h3 className="title-dota" style={{ fontSize: "1.1rem", color: "#fff", margin: 0 }}>
                  Live Win Probability Swings Timeline
                </h3>
                <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "2px 0 0 0" }}>
                  Real-time mathematical trajectory plotted across key match events
                </p>
              </div>

              {/* Scenario Preset Buttons */}
              <div style={{ display: "flex", gap: "6px" }}>
                <button onClick={() => loadScenario("laning")} className="btn-ghost" style={{ padding: "4px 8px", fontSize: "0.75rem" }}>
                  Laning (10m)
                </button>
                <button onClick={() => loadScenario("mid_push")} className="btn-ghost" style={{ padding: "4px 8px", fontSize: "0.75rem" }}>
                  Aegis Push (24m)
                </button>
                <button onClick={() => loadScenario("comeback")} className="btn-ghost" style={{ padding: "4px 8px", fontSize: "0.75rem" }}>
                  Comeback (35m)
                </button>
              </div>
            </div>

            {/* SVG Dynamic Timeline Graph */}
            <div style={{ position: "relative", width: "100%", height: `${chartH}px`, background: "#0b101a", borderRadius: "6px", border: "1px solid var(--border-subtle)", overflow: "hidden" }}>
              <svg viewBox={`0 0 ${chartW} ${chartH}`} style={{ width: "100%", height: "100%", display: "block" }}>
                <defs>
                  <linearGradient id="radAreaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00f59b" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#00f59b" stopOpacity="0.0" />
                  </linearGradient>
                  <linearGradient id="direAreaGrad" x1="0" y1="1" x2="0" y2="0">
                    <stop offset="0%" stopColor="#ff3344" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#ff3344" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* 50% Equilibrium Baseline */}
                <line x1={padL} y1={midY} x2={chartW - padR} y2={midY} stroke="rgba(255, 255, 255, 0.15)" strokeDasharray="4 4" strokeWidth="1" />
                <text x={padL - 6} y={midY + 4} fill="var(--text-faint)" fontSize="10" textAnchor="end" fontFamily="var(--font-mono)">50%</text>

                {/* 75% and 25% Grid lines */}
                <line x1={padL} y1={padT + 0.25 * (chartH - padT - padB)} x2={chartW - padR} y2={padT + 0.25 * (chartH - padT - padB)} stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1" />
                <text x={padL - 6} y={padT + 0.25 * (chartH - padT - padB) + 4} fill="var(--radiant-green)" fontSize="10" textAnchor="end" opacity="0.6" fontFamily="var(--font-mono)">75%</text>

                <line x1={padL} y1={padT + 0.75 * (chartH - padT - padB)} x2={chartW - padR} y2={padT + 0.75 * (chartH - padT - padB)} stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1" />
                <text x={padL - 6} y={padT + 0.75 * (chartH - padT - padB) + 4} fill="var(--dire-crimson)" fontSize="10" textAnchor="end" opacity="0.6" fontFamily="var(--font-mono)">25%</text>

                {/* Trajectory Polyline */}
                {svgPathD && (
                  <path
                    d={svgPathD}
                    fill="none"
                    stroke="var(--aegis-gold)"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ filter: "drop-shadow(0 0 6px rgba(245, 166, 35, 0.5))" }}
                  />
                )}

                {/* Event Markers & Nodes */}
                {chartPoints.map((pt, idx) => {
                  const isRadFavored = pt.radWinProb >= 50;
                  const nodeColor = pt.type === "roshan" ? "var(--aegis-gold)" : isRadFavored ? "var(--radiant-green)" : "var(--dire-crimson)";

                  return (
                    <g key={idx} onMouseEnter={() => setHoveredPoint(pt)} onMouseLeave={() => setHoveredPoint(null)} style={{ cursor: "pointer" }}>
                      <circle cx={pt.x} cy={pt.y} r={pt.type === "roshan" ? 6 : 4.5} fill="#0b101a" stroke={nodeColor} strokeWidth="2.5" />
                      {pt.type === "roshan" && (
                        <circle cx={pt.x} cy={pt.y} r="2" fill="var(--aegis-gold)" />
                      )}
                      <text x={pt.x} y={chartH - 10} fill="var(--text-faint)" fontSize="10" textAnchor="middle" fontFamily="var(--font-mono)">
                        {pt.minute}m
                      </text>
                    </g>
                  );
                })}
              </svg>

              {/* Hover Tooltip */}
              {hoveredPoint && (
                <div
                  className="chart-tooltip"
                  style={{
                    left: `${(hoveredPoint.x / chartW) * 100}%`,
                    top: `${hoveredPoint.y - 45}px`,
                    transform: "translateX(-50%)",
                  }}
                >
                  <div style={{ fontWeight: 700, color: hoveredPoint.radWinProb >= 50 ? "var(--radiant-green)" : "var(--dire-crimson)" }}>
                    Min {hoveredPoint.minute}:00 // {hoveredPoint.radWinProb}% Radiant Win
                  </div>
                  <div style={{ color: "#cbd5e1" }}>{hoveredPoint.event}</div>
                  <div style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>
                    Net Worth: {hoveredPoint.nwLead >= 0 ? `+${hoveredPoint.nwLead}g Radiant` : `${hoveredPoint.nwLead}g Dire`}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Graph 2: Net Worth Swing Graph & Objective Dominion */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            {/* Net Worth Graph Card */}
            <div className="glass-panel" style={{ padding: "1.2rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#fff", textTransform: "uppercase" }}>
                  Net Worth Differential
                </span>
                <span className="font-stats" style={{ color: netWorthLead >= 0 ? "var(--radiant-green)" : "var(--dire-crimson)", fontSize: "1.1rem" }}>
                  {netWorthLead >= 0 ? `+${netWorthLead.toLocaleString()}g` : `${netWorthLead.toLocaleString()}g`}
                </span>
              </div>

              {/* Visual Gold Delta Bar */}
              <div style={{ height: "14px", borderRadius: "7px", background: "#111722", position: "relative", overflow: "hidden", margin: "14px 0" }}>
                <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: "2px", background: "rgba(255, 255, 255, 0.3)", zIndex: 2 }} />
                {netWorthLead >= 0 ? (
                  <div style={{
                    position: "absolute",
                    left: "50%",
                    top: 0,
                    bottom: 0,
                    width: `${Math.min(50, (netWorthLead / 20000) * 50)}%`,
                    background: "linear-gradient(90deg, #00d084 0%, #00f59b 100%)",
                    borderRadius: "0 7px 7px 0",
                  }} />
                ) : (
                  <div style={{
                    position: "absolute",
                    right: "50%",
                    top: 0,
                    bottom: 0,
                    width: `${Math.min(50, (Math.abs(netWorthLead) / 20000) * 50)}%`,
                    background: "linear-gradient(90deg, #ff3344 0%, #ff4d5a 100%)",
                    borderRadius: "7px 0 0 7px",
                  }} />
                )}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                <span>Dire +20k</span>
                <span>0g Even</span>
                <span>Radiant +20k</span>
              </div>
            </div>

            {/* Map Control & Objective Dominion */}
            <div className="glass-panel" style={{ padding: "1.2rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#fff", textTransform: "uppercase" }}>
                  Map Vision & Objective Control
                </span>
                <span className="font-stats" style={{ color: "var(--aegis-gold)", fontSize: "1.1rem" }}>
                  {mapControl}% Radiant
                </span>
              </div>

              {/* Segmented Dominion Bar */}
              <div style={{ height: "14px", borderRadius: "7px", background: "#111722", overflow: "hidden", display: "flex", margin: "14px 0" }}>
                <div style={{ width: `${mapControl}%`, background: "linear-gradient(90deg, #00f59b 0%, #38bdf8 100%)", transition: "width 0.4s ease" }} />
                <div style={{ width: `${100 - mapControl}%`, background: "linear-gradient(90deg, #ff4d5a 0%, #ff3344 100%)", transition: "width 0.4s ease" }} />
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                <span style={{ color: "var(--radiant-green)" }}>Radiant: {mapControl}%</span>
                <span style={{ color: "var(--dire-crimson)" }}>Dire: {100 - mapControl}%</span>
              </div>
            </div>
          </div>

          {/* Interactive In-Game Event Injectors (What happens if changes happen in live game) */}
          <div className="glass-panel" style={{ padding: "1.2rem" }}>
            <h4 style={{ fontSize: "0.95rem", color: "#fff", marginBottom: "8px", textTransform: "uppercase" }}>
              ⚡ Simulate Live Event Triggers (Instant Probability Swings)
            </h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px" }}>
              <button
                onClick={() => triggerEvent("Radiant 4-Man Teamfight Wipe", 3200, 7.5, "teamwipe_radiant")}
                style={{
                  background: "rgba(0, 245, 155, 0.08)",
                  border: "1px solid rgba(0, 245, 155, 0.25)",
                  color: "var(--radiant-green)",
                  padding: "8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  textAlign: "left",
                }}
              >
                ⚔️ Radiant Wipes Dire (+7.5%)
              </button>

              <button
                onClick={() => triggerEvent("Dire Snatches Roshan & Aegis", -2800, -8.0, "roshan_dire")}
                style={{
                  background: "rgba(255, 51, 68, 0.08)",
                  border: "1px solid rgba(255, 51, 68, 0.25)",
                  color: "var(--dire-crimson)",
                  padding: "8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  textAlign: "left",
                }}
              >
                🛡️ Dire Steals Aegis (+8% Dire)
              </button>

              <button
                onClick={() => triggerEvent("Radiant Claims Roshan & Aegis", 2500, 7.0, "roshan_radiant")}
                style={{
                  background: "rgba(245, 166, 35, 0.08)",
                  border: "1px solid rgba(245, 166, 35, 0.25)",
                  color: "var(--aegis-gold)",
                  padding: "8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  textAlign: "left",
                }}
              >
                🛡️ Radiant Claims Aegis (+7%)
              </button>

              <button
                onClick={() => triggerEvent("Dire Tier 3 Tower Destroyed", 1800, 5.0, "tower_radiant")}
                style={{
                  background: "rgba(0, 245, 155, 0.08)",
                  border: "1px solid rgba(0, 245, 155, 0.25)",
                  color: "var(--radiant-green)",
                  padding: "8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  textAlign: "left",
                }}
              >
                🏰 Dire T3 Breached (+5%)
              </button>

              <button
                onClick={() => triggerEvent("Dire 4-Man Teamfight Wipe", -3200, -7.5, "teamwipe_dire")}
                style={{
                  background: "rgba(255, 51, 68, 0.08)",
                  border: "1px solid rgba(255, 51, 68, 0.25)",
                  color: "var(--dire-crimson)",
                  padding: "8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  textAlign: "left",
                }}
              >
                ⚔️ Dire Wipes Radiant (+7.5% Dire)
              </button>

              <button
                onClick={() => triggerEvent("Radiant Core Finishes BKB Spike", 1200, 3.5, "item_radiant")}
                style={{
                  background: "rgba(56, 189, 248, 0.08)",
                  border: "1px solid rgba(56, 189, 248, 0.25)",
                  color: "var(--mana-blue)",
                  padding: "8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  textAlign: "left",
                }}
              >
                ⚡ Core Finished BKB Spike (+3.5%)
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Live Controls & AI Tactical Coaching */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Live In-Game State Adjusters */}
          <div className="glass-panel" style={{ padding: "1.5rem" }}>
            <h3 className="title-dota" style={{ fontSize: "1.05rem", color: "#fff", marginBottom: "1rem" }}>
              Live Game State Sliders
            </h3>

            {/* Game Time Scrubber */}
            <div style={{ marginBottom: "1.2rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "4px" }}>
                <span style={{ color: "var(--text-muted)" }}>Game Clock</span>
                <span style={{ color: "var(--aegis-gold)", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                  {formattedTime} ({currentMinute} min)
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="3600"
                step="30"
                value={gameSeconds}
                onChange={(e) => setGameSeconds(Number(e.target.value))}
                style={{ width: "100%" }}
              />
            </div>

            {/* Net Worth Lead Slider */}
            <div style={{ marginBottom: "1.2rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "4px" }}>
                <span style={{ color: "var(--text-muted)" }}>Net Worth Advantage</span>
                <span style={{ color: netWorthLead >= 0 ? "var(--radiant-green)" : "var(--dire-crimson)", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                  {netWorthLead >= 0 ? `+${netWorthLead}g RAD` : `${netWorthLead}g DIRE`}
                </span>
              </div>
              <input
                type="range"
                min="-20000"
                max="20000"
                step="500"
                value={netWorthLead}
                onChange={(e) => setNetWorthLead(Number(e.target.value))}
                style={{ width: "100%" }}
              />
            </div>

            {/* Roshan & Aegis Status Dropdown */}
            <div>
              <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
                Roshan / Aegis Claim Status
              </label>
              <select
                value={roshanState}
                onChange={(e) => {
                  setRoshanState(e.target.value);
                  if (e.target.value.includes("aegis")) setAegisSecondsLeft(300);
                  else setAegisSecondsLeft(0);
                }}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "4px",
                  background: "#111722",
                  border: "1px solid var(--border-subtle)",
                  color: "#fff",
                  fontSize: "0.85rem",
                }}
              >
                <option value="alive">Roshan Alive in Pit</option>
                <option value="dead">Roshan Slain (Respawning 8-11 min)</option>
                <option value="aegis_radiant">Aegis Held by Radiant Core</option>
                <option value="aegis_dire">Aegis Held by Dire Core</option>
              </select>
            </div>
          </div>

          {/* AI Tactical Coach Directives (Conditioned on Live State) */}
          <div className="glass-panel" style={{ padding: "1.5rem", borderTop: "3px solid var(--mana-blue)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Zap size={18} color="var(--mana-blue)" />
                <h3 className="title-dota" style={{ fontSize: "1.05rem", color: "#fff", margin: 0 }}>
                  Live Tactical AI Directives
                </h3>
              </div>
              <button
                onClick={copyBriefing}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                  background: copiedBriefing ? "rgba(0, 245, 155, 0.15)" : "rgba(255, 255, 255, 0.05)",
                  border: `1px solid ${copiedBriefing ? "var(--radiant-green)" : "var(--border-subtle)"}`,
                  color: copiedBriefing ? "var(--radiant-green)" : "var(--text-muted)",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  fontSize: "0.75rem",
                  cursor: "pointer",
                }}
              >
                {copiedBriefing ? <Check size={12} /> : <Copy size={12} />}
                {copiedBriefing ? "Copied" : "Copy"}
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {coachDirectives.map((dir, idx) => (
                <div
                  key={idx}
                  style={{
                    background: "rgba(255, 255, 255, 0.02)",
                    borderLeft: `3px solid ${
                      dir.type === "aggressive" ? "var(--aegis-gold)" : dir.type === "defensive" ? "var(--dire-crimson)" : "var(--mana-blue)"
                    }`,
                    padding: "10px 12px",
                    borderRadius: "0 4px 4px 0",
                  }}
                >
                  <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#fff", marginBottom: "3px" }}>
                    {dir.title}
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "#cbd5e1", lineHeight: 1.4 }}>
                    {dir.text}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
