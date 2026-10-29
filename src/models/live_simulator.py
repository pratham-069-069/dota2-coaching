"""
Live Game Simulator (Model 6):
Simulates a live Dota 2 match in progress on top of the XGBoost draft prior.
Given two drafts, a game clock, a seed and a stream of in-game events
(kills, teamfights, Roshan, towers, first blood), it produces:
  - a per-minute net gold advantage timeline
  - a per-minute Radiant win probability timeline
  - event-level gold / probability impact attribution
  - momentum and a forward AI projection to the 60-minute mark
What-if scenarios are supported by re-running the same seeded base timeline
with different injected events and contrasted draft priors.
"""

from typing import Dict, List, Optional, Any
import math

import numpy as np

from src.data.features import HERO_ID_TO_NAME

GAME_LENGTH = 60

# Per-minute gold drift from draft edge (edge of 0.5 => +150 g/min mid game).
DRIFT_X = [0, 10, 20, 30, 40, 60]
DRIFT_Y = [0.0, 48.0, 92.0, 150.0, 210.0, 300.0]

# Beta curve: gold advantage -> logit odds scaling per game minute.
# Empirically anchored: 5k gold lead ~65-70% WR at 20 min, ~80% at 30, ~95% late.
BETA_BENCHMARKS_X = [0, 8, 12, 20, 28, 36, 45, 60]
BETA_BENCHMARKS_Y = [0.0, 0.00006, 0.0001, 0.00015, 0.00022, 0.00032, 0.00048, 0.0008]

EVENT_LABELS = {
    "first_blood": "First blood",
    "kill": "Pick-off kill",
    "teamfight": "Teamfight",
    "roshan": "Roshan secured",
    "tower": "Tower destroyed",
    "ward_sweep": "Vision sweep",
}

EVENT_ICONS = {
    "first_blood": "🩸",
    "kill": "⚔️",
    "teamfight": "💥",
    "roshan": "🐉",
    "tower": "🏰",
    "ward_sweep": "👁️",
}


def _sigmoid(x: float) -> float:
    x = max(-25.0, min(25.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


class LiveGameSimulator:
    """Stateless seeded simulation of a live match on top of a draft prior."""

    def __init__(self, draft_advisor):
        self.draft_advisor = draft_advisor

    # ------------------------------------------------------------------
    # Seeded event stream generation
    # ------------------------------------------------------------------
    def _generate_auto_events(self, radiant_heroes: List[int], dire_heroes: List[int],
                              seed: int) -> List[Dict[str, Any]]:
        """Generates a deterministic 60-minute plausible event stream for the draft."""
        rng = np.random.default_rng(int(seed) + int(sum(radiant_heroes)) * 977
                                    + int(sum(dire_heroes)) * 1301)
        prior = 0.5
        try:
            if radiant_heroes or dire_heroes:
                prior = float(self.draft_advisor.predict_win_probability(radiant_heroes, dire_heroes)
                              ["radiant_win_prob"])
        except Exception:
            prior = 0.5
        edge = prior - 0.5  # -0.5 .. +0.5, positive favors Radiant

        events: List[Dict[str, Any]] = []

        # First blood — minute 1 to 6, 93% of games
        if rng.random() < 0.93:
            fb_min = int(1 + rng.random() * 5)
            fb_team = "radiant" if rng.random() < 0.5 + edge * 0.6 else "dire"
            events.append({"minute": fb_min, "team": fb_team, "type": "first_blood"})

        # Skirmish kills and teamfights per minute
        for minute in range(0, GAME_LENGTH):
            # Kill intensity ramps up mid game
            intensity = 0.30 if minute < 10 else (0.55 if minute < 34 else 0.38)
            side_bias = 0.5 + edge * 0.55
            while rng.random() < intensity:
                team = "radiant" if rng.random() < side_bias else "dire"
                events.append({"minute": minute, "team": team, "type": "kill",
                               "count": int(1 + rng.random() * 2)})

            # Teamfights: chunky events from ~8 min onward
            if minute >= 8 and rng.random() < (0.045 if minute < 30 else 0.065):
                team = "radiant" if rng.random() < side_bias else "dire"
                events.append({"minute": minute, "team": team, "type": "teamfight",
                               "count": int(2 + rng.random() * 3)})

            # Roshan from ~minute 12
            if minute >= 12 and rng.random() < 0.022:
                team = "radiant" if rng.random() < side_bias else "dire"
                events.append({"minute": minute, "team": team, "type": "roshan"})

            # Towers from ~minute 9, more likely after a favorable drift
            if minute >= 9 and rng.random() < 0.030 + max(0.0, edge * 0.03):
                team = "radiant" if rng.random() < side_bias else "dire"
                events.append({"minute": minute, "team": team, "type": "tower"})

            # Rare gank-deny vision plays for flavour
            if minute > 6 and rng.random() < 0.03:
                team = "radiant" if rng.random() < 0.5 + edge * 0.4 else "dire"
                events.append({"minute": minute, "team": team, "type": "ward_sweep"})

        events.sort(key=lambda e: e["minute"])
        return events

    # ------------------------------------------------------------------
    # Event valuation
    # ------------------------------------------------------------------
    def _event_gold(self, ev: Dict[str, Any]) -> float:
        """Net gold swing (positive = good for the acting team)."""
        t = ev["minute"]
        typ = ev["type"]
        if typ == "first_blood":
            return 620.0
        if typ == "kill":
            base = 260.0 + 14.0 * min(t, 50)
            stable = ((ev["minute"] * 73 + len(typ) * 29 + (59 if ev["team"] == "radiant" else 17)) % 41) / 100.0
            return base * max(1, ev.get("count", 1)) * (0.9 + stable)
        if typ == "teamfight":
            base = (300.0 + 22.0 * min(t, 55)) * max(2, ev.get("count", 3))
            return base
        if typ == "roshan":
            return 2150.0 + 18.0 * min(t, 55)
        if typ == "tower":
            return 900.0 + 22.0 * min(t, 55)
        if typ == "ward_sweep":
            return 0.0
        return 0.0

    # ------------------------------------------------------------------
    # Core simulation
    # ------------------------------------------------------------------
    def simulate(
        self,
        radiant_heroes: List[int],
        dire_heroes: List[int],
        minute: int,
        seed: int = 0,
        extra_events: Optional[List[Dict[str, Any]]] = None,
        include_projection: bool = True,
    ) -> Dict[str, Any]:
        minute = max(0, min(int(minute), GAME_LENGTH))
        extra_events = extra_events or []

        # Draft prior (anchor probability at minute 0)
        try:
            prior = float(self.draft_advisor.predict_win_probability(radiant_heroes, dire_heroes)
                          ["radiant_win_prob"])
        except Exception:
            prior = 0.5

        # Compose event stream: seeded auto events + user injections, sorted
        user_events = []
        for ev in extra_events:
            user_events.append({
                "minute": int(ev.get("minute", minute)),
                "team": ev.get("team", "radiant"),
                "type": ev.get("type", "kill"),
                "count": ev.get("count", 1),
                "manual": True,
            })
        auto_events = self._generate_auto_events(radiant_heroes, dire_heroes, seed)
        all_events = sorted(auto_events + user_events, key=lambda e: (e["minute"], e["type"] != "first_blood"))

        # Per-minute net gold timeline
        up_to = GAME_LENGTH if include_projection else minute
        edge = prior - 0.5
        gold_adv = [0.0] * (up_to + 1)
        processed: List[Dict[str, Any]] = []
        event_idx = 0
        for t in range(up_to + 1):
            carry = gold_adv[t - 1] if t > 0 else 0.0
            drift = float(np.interp(t, DRIFT_X, DRIFT_Y)) * 2.0 * edge
            net = carry + drift
            while event_idx < len(all_events) and all_events[event_idx]["minute"] <= t:
                ev = all_events[event_idx]
                if ev["minute"] <= minute:
                    g = self._event_gold(ev)
                    if ev["team"] == "dire":
                        g = -g
                    net += g
                    ev["gold_swing"] = round(g if ev["team"] == "radiant" else -g, 1)
                    ev["label"] = EVENT_LABELS.get(ev["type"], ev["type"])
                    ev["icon"] = EVENT_ICONS.get(ev["type"], "•")
                    # probability impact (before vs after realization)
                    p_before = self._prob_from_logit(prior, t - 1, carry, edge)
                    p_after = self._prob_from_logit(prior, t, net, edge)
                    ev["prob_impact"] = round((p_after - p_before) * 100.0, 2)
                    processed.append(ev)
                event_idx += 1
            gold_adv[t] = net

        # Timeline with probability + momentum
        timeline = []
        for t in range(up_to + 1):
            realized = gold_adv[t]
            p = self._prob_from_logit(prior, t, realized, edge)
            recent = realized - (gold_adv[max(0, t - 4)] if t >= 4 else 0.0)
            momentum = float(np.clip(50 + recent / 90.0, 2, 98))
            timeline.append({
                "minute": t,
                "gold_advantage": round(realized, 1),
                "radiant_win_prob": round(p, 4),
                "momentum_radiant": round(momentum, 1),
            })

        realized_timeline = timeline[: minute + 1]
        current = realized_timeline[-1]

        result = {
            "draft_prior": {"radiant_win_prob": round(prior, 4),
                            "dire_win_prob": round(1 - prior, 4)},
            "current": {
                "minute": minute,
                "radiant_win_prob": current["radiant_win_prob"],
                "dire_win_prob": round(1 - current["radiant_win_prob"], 4),
                "gold_advantage": current["gold_advantage"],
                "momentum_radiant": current["momentum_radiant"],
                "total_events": len(processed),
            },
            "timeline": realized_timeline,
            "projection": timeline[minute:] if include_projection and minute < GAME_LENGTH else [],
            "events": processed[: min(len(processed), 120)],
            "event_counts": self._count_events(processed),
        }

        result["commentary"] = self._narrate(result, radiant_heroes, dire_heroes)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _prob_from_logit(self, prior: float, t: int, gold_adv: float, edge: float) -> float:
        beta = float(np.interp(t, BETA_BENCHMARKS_X, BETA_BENCHMARKS_Y))
        draft_weight = 1.0 - 0.45 * min(max(t, 0), 60) / 60.0
        return _sigmoid(_logit(prior) * draft_weight + beta * gold_adv)

    def _count_events(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {"radiant": 0, "dire": 0}
        for ev in events:
            counts[ev["team"]] += 1
        counts["roshan_radiant"] = sum(1 for e in events if e["type"] == "roshan" and e["team"] == "radiant")
        counts["roshan_dire"] = sum(1 for e in events if e["type"] == "roshan" and e["team"] == "dire")
        counts["towers_radiant"] = sum(1 for e in events if e["type"] == "tower" and e["team"] == "radiant")
        counts["towers_dire"] = sum(1 for e in events if e["type"] == "tower" and e["team"] == "dire")
        return counts

    def _hero_names(self, ids: List[int]) -> str:
        return ", ".join(HERO_ID_TO_NAME.get(int(h), f"Hero {h}") for h in ids) or "unknown"

    def _narrate(self, result: Dict[str, Any], radiant_heroes: List[int], dire_heroes: List[int]) -> List[str]:
        """Generates short observer-style commentary for the current state."""
        cur = result["current"]
        prior = result["draft_prior"]["radiant_win_prob"]
        live = cur["radiant_win_prob"]
        gold = cur["gold_advantage"]
        bullet = []

        swing = live - prior
        if gold >= 0:
            bullet.append(
                f"Radiant holds a {gold:,.0f}g net advantage at {cur['minute']}': live win prob "
                f"{live * 100:.1f}% vs draft prior {prior * 100:.1f}% ({swing * 100:+.1f} pts)."
            )
        else:
            bullet.append(
                f"Dire seizes the tempo with a {abs(gold):,.0f}g net lead at {cur['minute']}': Radiant live win prob "
                f"{live * 100:.1f}% vs draft prior {prior * 100:.1f}% ({swing * 100:+.1f} pts)."
            )
        if cur["momentum_radiant"] >= 62:
            bullet.append("🟢 Radiant is snowballing — recent skirmishes converted into real estate.")
        elif cur["momentum_radiant"] <= 38:
            bullet.append("🔴 Dire control window — Radiant should buy space, not split-push.")
        else:
            bullet.append("⚖️ Early-even game — the next Roshan or mid T2 will decide the curve.")
        bullet.append(f"Draft: Radiant [{self._hero_names(radiant_heroes)}] vs Dire [{self._hero_names(dire_heroes)}]")
        return bullet
