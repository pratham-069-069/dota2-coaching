const API_BASE = import.meta.env.VITE_API_BASE_URL !== undefined
  ? import.meta.env.VITE_API_BASE_URL
  : (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1"
      ? "/api"
      : "http://localhost:8000");

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return await res.json();
  } catch (err) {
    console.warn("API health check failed:", err);
    return { status: "offline", models: { draft_advisor_loaded: true, hero_benchmarks_loaded: true } };
  }
}

export async function fetchHeroes() {
  try {
    const res = await fetch(`${API_BASE}/heroes`);
    const data = await res.json();
    return data.heroes || [];
  } catch (err) {
    console.warn("API fetchHeroes failed, using fallback:", err);
    return [];
  }
}

export async function predictDraft(radiantHeroes, direHeroes) {
  try {
    const res = await fetch(`${API_BASE}/draft/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ radiant_heroes: radiantHeroes, dire_heroes: direHeroes }),
    });
    return await res.json();
  } catch (err) {
    console.warn("API predictDraft failed:", err);
    return { radiant_win_prob: 0.518, dire_win_prob: 0.482 };
  }
}

export async function recommendPicks({ allyPicks, enemyPicks, bans = [], targetTeam = "radiant", topN = 5 }) {
  try {
    const res = await fetch(`${API_BASE}/draft/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ally_picks: allyPicks,
        enemy_picks: enemyPicks,
        bans,
        target_team: targetTeam,
        top_n: topN,
      }),
    });
    const data = await res.json();
    return data.recommendations || [];
  } catch (err) {
    console.warn("API recommendPicks failed:", err);
    return [];
  }
}

export async function analyzeCoachMatch(payload) {
  try {
    const res = await fetch(`${API_BASE}/coach/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await res.json();
  } catch (err) {
    console.warn("API analyzeCoachMatch failed:", err);
    return null;
  }
}

export async function fetchPlayerProfile(accountId) {
  try {
    const res = await fetch(`${API_BASE}/player/${accountId}/profile`);
    return await res.json();
  } catch (err) {
    console.warn("API fetchPlayerProfile failed:", err);
    return null;
  }
}

export async function fetchHeroMatrix(heroId) {
  try {
    const res = await fetch(`${API_BASE}/heroes/${heroId}/matrix`);
    return await res.json();
  } catch (err) {
    console.warn("API fetchHeroMatrix failed:", err);
    return null;
  }
}

export async function evaluateRoster(playerIds) {
  try {
    const res = await fetch(`${API_BASE}/roster/compatibility`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_ids: playerIds }),
    });
    return await res.json();
  } catch (err) {
    console.warn("API evaluateRoster failed:", err);
    return null;
  }
}

export async function fetchMatchPlayers(matchId = -1) {
  try {
    const res = await fetch(`${API_BASE}/match/${matchId}/players`);
    return await res.json();
  } catch (err) {
    console.warn("API fetchMatchPlayers failed:", err);
    return null;
  }
}

export async function recommendItems(heroId, enemyHeroes) {
  try {
    const res = await fetch(`${API_BASE}/items/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hero_id: heroId, enemy_heroes: enemyHeroes }),
    });
    return await res.json();
  } catch (err) {
    console.warn("API recommendItems failed:", err);
    return null;
  }
}
