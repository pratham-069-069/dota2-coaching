import React from "react";
import { Swords, ClipboardCheck, UserCheck, Compass, Activity, ShieldAlert } from "lucide-react";

export default function Header({ activeTab, setActiveTab, apiOnline }) {
  const navItems = [
    { id: "draft", label: "Draft Room", icon: Swords },
    { id: "live", label: "Live Simulator", icon: Activity, isLive: true },
    { id: "coach", label: "Between-Match Coach", icon: ClipboardCheck },
    { id: "scout", label: "Player Profiler", icon: UserCheck },
    { id: "matrix", label: "Synergy & Counters", icon: Compass },
  ];

  return (
    <header style={{
      borderBottom: "1px solid var(--border-subtle)",
      background: "rgba(10, 14, 22, 0.85)",
      backdropFilter: "blur(20px)",
      position: "sticky",
      top: 0,
      zIndex: 100,
      padding: "0 2rem",
    }}>
      <div style={{
        maxWidth: "1400px",
        margin: "0 auto",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: "72px",
      }}>
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "42px",
            height: "42px",
            borderRadius: "10px",
            background: "linear-gradient(135deg, #f5a623 0%, #ff3344 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 15px rgba(245, 166, 35, 0.35)",
          }}>
            <span style={{ fontFamily: "var(--font-dota)", fontWeight: 900, color: "#fff", fontSize: "1.3rem" }}>Ω</span>
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span className="title-dota" style={{ fontSize: "1.25rem", fontWeight: 800, color: "#fff", letterSpacing: "0.08em" }}>
                AEGIS
              </span>
              <span className="badge badge-gold" style={{ fontSize: "0.65rem" }}>
                v2.05 PRODUCTION LIVE
              </span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)", letterSpacing: "0.04em" }}>
              DOTA 2 COACHING INTELLIGENCE PLATFORM
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: "flex", gap: "6px" }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 16px",
                  borderRadius: "var(--radius-sm)",
                  background: isActive ? "rgba(245, 166, 35, 0.12)" : "transparent",
                  color: isActive ? "var(--aegis-gold)" : "var(--text-muted)",
                  border: isActive ? "1px solid rgba(245, 166, 35, 0.4)" : "1px solid transparent",
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                  fontSize: "0.95rem",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                {item.isLive ? (
                  <span className="live-indicator-dot" style={{ width: "7px", height: "7px" }} />
                ) : (
                  <Icon size={18} color={isActive ? "var(--aegis-gold)" : "var(--text-faint)"} />
                )}
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* System Status Pill */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "7px",
            background: apiOnline ? "rgba(0, 245, 155, 0.1)" : "rgba(255, 51, 68, 0.1)",
            border: `1px solid ${apiOnline ? "rgba(0, 245, 155, 0.3)" : "rgba(255, 51, 68, 0.3)"}`,
            padding: "5px 12px",
            borderRadius: "20px",
            fontFamily: "var(--font-mono)",
            fontSize: "0.8rem",
            color: apiOnline ? "var(--radiant-green)" : "var(--dire-crimson)",
          }}>
            <span style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              background: apiOnline ? "var(--radiant-green)" : "var(--dire-crimson)",
              boxShadow: apiOnline ? "0 0 8px var(--radiant-green)" : "0 0 8px var(--dire-crimson)",
            }} />
            {apiOnline ? "MODELS ONLINE // 50K MATCHES" : "OFFLINE"}
          </div>
        </div>
      </div>
    </header>
  );
}
