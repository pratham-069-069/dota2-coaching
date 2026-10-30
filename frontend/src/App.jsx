import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import DraftRoom from "./components/DraftRoom";
import LiveSimulator from "./components/LiveSimulator";
import BetweenMatchCoach from "./components/BetweenMatchCoach";
import PlayerScout from "./components/PlayerScout";
import MatrixExplorer from "./components/MatrixExplorer";
import { fetchHealth, fetchHeroes } from "./services/api";

export default function App() {
  const [activeTab, setActiveTab] = useState("draft");
  const [apiOnline, setApiOnline] = useState(true);
  const [heroes, setHeroes] = useState([]);

  useEffect(() => {
    async function init() {
      const health = await fetchHealth();
      setApiOnline(health.status === "healthy");

      const heroList = await fetchHeroes();
      if (heroList.length > 0) {
        setHeroes(heroList);
      } else {
        // Fallback popular hero roster
        setHeroes([
          { hero_id: 1, name: "Anti-Mage", win_rate: 0.518 },
          { hero_id: 2, name: "Axe", win_rate: 0.524 },
          { hero_id: 3, name: "Bane", win_rate: 0.509 },
          { hero_id: 4, name: "Bloodseeker", win_rate: 0.512 },
          { hero_id: 5, name: "Crystal Maiden", win_rate: 0.531 },
          { hero_id: 8, name: "Juggernaut", win_rate: 0.528 },
          { hero_id: 14, name: "Pudge", win_rate: 0.505 },
          { hero_id: 25, name: "Lina", win_rate: 0.498 },
          { hero_id: 26, name: "Lion", win_rate: 0.489 },
          { hero_id: 44, name: "Phantom Assassin", win_rate: 0.515 },
          { hero_id: 74, name: "Invoker", win_rate: 0.495 },
          { hero_id: 86, name: "Rubick", win_rate: 0.472 },
          { hero_id: 102, name: "Abaddon", win_rate: 0.548 },
        ]);
      }
    }
    init();
  }, []);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header activeTab={activeTab} setActiveTab={setActiveTab} apiOnline={apiOnline} />

      <main style={{ flex: 1, padding: "0 2rem 2rem 2rem" }}>
        {activeTab === "draft" && <DraftRoom heroes={heroes} />}
        {activeTab === "live" && <LiveSimulator heroes={heroes} />}
        {activeTab === "coach" && <BetweenMatchCoach heroes={heroes} />}
        {activeTab === "scout" && <PlayerScout heroes={heroes} />}
        {activeTab === "matrix" && <MatrixExplorer heroes={heroes} />}
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: "1px solid var(--border-subtle)",
        background: "rgba(10, 14, 22, 0.9)",
        padding: "1.2rem 2rem",
        fontSize: "0.8rem",
        color: "var(--text-faint)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        maxWidth: "100%",
        fontFamily: "var(--font-mono)",
      }}>
        <div>
          AEGIS COACHING ENGINE // 50,000 MATCHES ANALYZED // XGBOOST DRAFT MODEL (AUC: 0.6378)
        </div>
        <div>
          TRUESKILL™ RATING SYSTEM // EMPIRICAL PERCENTILE BENCHMARKING
        </div>
      </footer>
    </div>
  );
}
