"""
Draft Advisor (Model 1):
Machine learning model and recommendation engine for Dota 2 drafting.
Trained on competitive match drafts to predict win probability and recommend
optimal hero picks considering team synergies and enemy counters.
"""

import json
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, log_loss
from xgboost import XGBClassifier

from src.data.config import FEATURES_DIR, MODELS_DIR
from src.data.features import (
    ALL_HERO_IDS,
    HERO_ID_TO_IDX,
    IDX_TO_HERO_ID,
    HERO_ID_TO_NAME,
    NUM_HEROES,
    build_draft_feature_matrix,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODEL_FILE = MODELS_DIR / "draft_xgb_model.pkl"
META_FILE = MODELS_DIR / "draft_model_meta.json"


class DraftAdvisor:
    def __init__(self):
        self.model: Optional[XGBClassifier] = None
        self.feature_names: List[str] = []
        self.hero_stats: Dict[int, Dict[str, Any]] = {}
        self.synergy_dict: Dict[Tuple[int, int], float] = {}  # (min_id, max_id) -> synergy_score
        self.counter_dict: Dict[Tuple[int, int], float] = {}  # (hero_id, enemy_id) -> advantage
        self.metadata: Dict[str, Any] = {}
        self._load_knowledge()

    def _load_knowledge(self):
        """Loads hero stats, synergy, and counter features from disk."""
        stats_path = FEATURES_DIR / "hero_stats.parquet"
        synergy_path = FEATURES_DIR / "hero_synergy.parquet"
        counter_path = FEATURES_DIR / "hero_counter.parquet"

        if stats_path.exists():
            df_stats = pd.read_parquet(stats_path)
            for _, r in df_stats.iterrows():
                hid = int(r["hero_id"])
                self.hero_stats[hid] = {
                    "name": r["localized_name"],
                    "win_rate": float(r["win_rate"]),
                    "pick_rate": float(r["pick_rate"]),
                    "picks": int(r["picks"]),
                }

        if synergy_path.exists():
            df_syn = pd.read_parquet(synergy_path)
            for _, r in df_syn.iterrows():
                pair = tuple(sorted((int(r["hero_1"]), int(r["hero_2"]))))
                self.synergy_dict[pair] = float(r["synergy_score"])

        if counter_path.exists():
            df_cnt = pd.read_parquet(counter_path)
            for _, r in df_cnt.iterrows():
                self.counter_dict[(int(r["hero"]), int(r["opponent"]))] = float(r["advantage"])

    def train(self, test_size: float = 0.2, random_state: int = 42) -> Dict[str, float]:
        """Trains the Draft Advisor XGBoost classifier on 50k match drafts."""
        drafts_path = FEATURES_DIR / "match_drafts.parquet"
        stats_path = FEATURES_DIR / "hero_stats.parquet"

        if not drafts_path.exists() or not stats_path.exists():
            raise FileNotFoundError("Run feature generation first (features.py)!")

        drafts_df = pd.read_parquet(drafts_path)
        hero_stats_df = pd.read_parquet(stats_path)

        logger.info(f"Building draft feature matrix for {len(drafts_df)} matches...")
        X, y, self.feature_names = build_draft_feature_matrix(drafts_df, hero_stats_df)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        logger.info(f"Training XGBoost Draft Model on {len(X_train)} samples...")
        self.model = XGBClassifier(
            n_estimators=180,
            learning_rate=0.08,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=random_state,
            n_jobs=-1,
        )

        self.model.fit(X_train, y_train)

        # Evaluation
        y_prob = self.model.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)

        auc = float(roc_auc_score(y_test, y_prob))
        acc = float(accuracy_score(y_test, y_pred))
        loss = float(log_loss(y_test, y_prob))

        metrics = {
            "test_auc_roc": round(auc, 4),
            "test_accuracy": round(acc, 4),
            "test_log_loss": round(loss, 4),
            "total_matches": len(drafts_df),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
        }

        self.metadata = metrics
        self.save_model()
        logger.info(f"Model trained successfully! Test AUC: {auc:.4f}, Accuracy: {acc * 100:.2f}%")
        return metrics

    def save_model(self):
        """Saves trained model and metadata."""
        with open(MODEL_FILE, "wb") as f:
            pickle.dump({"model": self.model, "feature_names": self.feature_names}, f)
        with open(META_FILE, "w") as f:
            json.dump(self.metadata, f, indent=2)
        logger.info(f"Model saved to {MODEL_FILE}")

    def load_model(self) -> bool:
        """Loads model from disk if available."""
        if MODEL_FILE.exists():
            with open(MODEL_FILE, "rb") as f:
                data = pickle.load(f)
                self.model = data["model"]
                self.feature_names = data["feature_names"]
            if META_FILE.exists():
                with open(META_FILE, "r") as f:
                    self.metadata = json.load(f)
            logger.info("Draft Advisor model loaded from disk.")
            return True
        return False

    def _create_feature_vector(self, radiant_heroes: List[int], dire_heroes: List[int]) -> np.ndarray:
        """Constructs the model feature vector for a given matchup."""
        X_diff = np.zeros(NUM_HEROES, dtype=np.float32)
        for h in radiant_heroes:
            if h in HERO_ID_TO_IDX:
                X_diff[HERO_ID_TO_IDX[h]] = 1.0
        for h in dire_heroes:
            if h in HERO_ID_TO_IDX:
                X_diff[HERO_ID_TO_IDX[h]] = -1.0

        r_wrs = [self.hero_stats.get(h, {}).get("win_rate", 0.5) for h in radiant_heroes]
        d_wrs = [self.hero_stats.get(h, {}).get("win_rate", 0.5) for h in dire_heroes]
        r_prs = [self.hero_stats.get(h, {}).get("pick_rate", 0.05) for h in radiant_heroes]
        d_prs = [self.hero_stats.get(h, {}).get("pick_rate", 0.05) for h in dire_heroes]

        r_avg = float(np.mean(r_wrs)) if r_wrs else 0.5
        d_avg = float(np.mean(d_wrs)) if d_wrs else 0.5
        r_pr_sum = float(np.sum(r_prs)) if r_prs else 0.0
        d_pr_sum = float(np.sum(d_prs)) if d_prs else 0.0

        agg_features = np.array([r_avg, d_avg, r_avg - d_avg, r_pr_sum, d_pr_sum], dtype=np.float32)
        return np.concatenate([X_diff, agg_features]).reshape(1, -1)

    def predict_win_probability(self, radiant_heroes: List[int], dire_heroes: List[int]) -> Dict[str, float]:
        """
        Predicts radiant and dire win probabilities given 5v5 or partial drafts.
        """
        if self.model is None:
            if not self.load_model():
                raise RuntimeError("Model is not loaded or trained. Call train() first.")

        feat = self._create_feature_vector(radiant_heroes, dire_heroes)
        rad_prob = float(self.model.predict_proba(feat)[0, 1])
        dire_prob = 1.0 - rad_prob

        return {
            "radiant_win_prob": round(rad_prob, 4),
            "dire_win_prob": round(dire_prob, 4),
        }

    def compute_team_synergy(self, team_heroes: List[int]) -> float:
        """Computes average synergy score among all pairs in a team."""
        if len(team_heroes) < 2:
            return 0.0
        scores = []
        for i in range(len(team_heroes)):
            for j in range(i + 1, len(team_heroes)):
                pair = tuple(sorted((team_heroes[i], team_heroes[j])))
                scores.append(self.synergy_dict.get(pair, 0.0))
        return float(np.mean(scores)) if scores else 0.0

    def compute_counter_advantage(self, ally_heroes: List[int], enemy_heroes: List[int]) -> float:
        """Computes net counter advantage for ally team against enemy team."""
        if not ally_heroes or not enemy_heroes:
            return 0.0
        advantages = []
        for a in ally_heroes:
            for e in enemy_heroes:
                advantages.append(self.counter_dict.get((a, e), 0.0))
        return float(np.mean(advantages)) if advantages else 0.0

    def recommend_picks(
        self,
        ally_picks: List[int],
        enemy_picks: List[int],
        bans: Optional[List[int]] = None,
        target_team: str = "radiant",
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Recommends the best hero picks for the current draft state.
        
        Evaluates candidate heroes across:
          - Model win probability gain
          - Synergy with existing ally heroes
          - Counter advantage against enemy heroes
          - Hero meta strength
        """
        if self.model is None and not self.load_model():
            raise RuntimeError("Model is not loaded or trained. Call train() first.")

        bans = bans or []
        banned_or_picked = set(ally_picks + enemy_picks + bans)
        candidates = [h for h in ALL_HERO_IDS if h not in banned_or_picked and h in self.hero_stats]

        # Baseline win probability
        if target_team.lower() == "radiant":
            base_prob = self.predict_win_probability(ally_picks, enemy_picks)["radiant_win_prob"]
        else:
            base_prob = self.predict_win_probability(enemy_picks, ally_picks)["dire_win_prob"]

        recommendations = []

        for cand in candidates:
            cand_allies = ally_picks + [cand]
            cand_name = self.hero_stats[cand]["name"]
            cand_base_wr = self.hero_stats[cand]["win_rate"]

            # 1. Projected Win Probability
            if target_team.lower() == "radiant":
                proj_prob = self.predict_win_probability(cand_allies, enemy_picks)["radiant_win_prob"]
            else:
                proj_prob = self.predict_win_probability(enemy_picks, cand_allies)["dire_win_prob"]
            prob_gain = proj_prob - base_prob

            # 2. Synergy with allies
            pair_synergies = []
            synergy_reasons = []
            for ally in ally_picks:
                pair = tuple(sorted((cand, ally)))
                syn_val = self.synergy_dict.get(pair, 0.0)
                pair_synergies.append(syn_val)
                if syn_val >= 0.03:
                    synergy_reasons.append(f"+{syn_val*100:.1f}% combo with {self.hero_stats.get(ally, {}).get('name', ally)}")
            avg_synergy = float(np.mean(pair_synergies)) if pair_synergies else 0.0

            # 3. Counter advantage vs enemies
            counter_advantages = []
            counter_reasons = []
            for enemy in enemy_picks:
                adv_val = self.counter_dict.get((cand, enemy), 0.0)
                counter_advantages.append(adv_val)
                if adv_val >= 0.03:
                    counter_reasons.append(f"+{adv_val*100:.1f}% counter vs {self.hero_stats.get(enemy, {}).get('name', enemy)}")
                elif adv_val <= -0.03:
                    counter_reasons.append(f"{adv_val*100:.1f}% weak vs {self.hero_stats.get(enemy, {}).get('name', enemy)}")
            avg_counter = float(np.mean(counter_advantages)) if counter_advantages else 0.0

            # Composite recommendation score
            composite_score = (
                0.45 * proj_prob +
                0.25 * (cand_base_wr) +
                0.15 * (0.5 + avg_synergy) +
                0.15 * (0.5 + avg_counter)
            )

            # Build tactical rationale explanation
            reasons = []
            if prob_gain > 0.01:
                reasons.append(f"Increases team win probability by +{prob_gain*100:.1f}%")
            reasons.extend(counter_reasons[:2])
            reasons.extend(synergy_reasons[:2])
            if not reasons:
                reasons.append(f"Solid overall pick ({cand_base_wr*100:.1f}% base win rate)")

            recommendations.append({
                "hero_id": int(cand),
                "hero_name": str(cand_name),
                "projected_win_prob": float(round(proj_prob, 4)),
                "win_prob_gain": float(round(prob_gain, 4)),
                "base_win_rate": float(round(cand_base_wr, 4)),
                "synergy_score": float(round(avg_synergy, 4)),
                "counter_advantage": float(round(avg_counter, 4)),
                "composite_score": float(round(composite_score, 4)),
                "reasons": [str(r) for r in reasons],
            })

        # Rank by composite score
        recommendations.sort(key=lambda x: x["composite_score"], reverse=True)
        return recommendations[:top_n]


if __name__ == "__main__":
    advisor = DraftAdvisor()
    print("Training draft advisor...")
    metrics = advisor.train()
    print("Metrics:", metrics)

    # Test recommendation
    print("\n--- Testing Draft Recommendation ---")
    ally = [1, 5]  # Anti-Mage, Crystal Maiden
    enemy = [8, 14]  # Juggernaut, Pudge
    recs = advisor.recommend_picks(ally, enemy, target_team="radiant", top_n=3)
    for r in recs:
        print(f"[{r['hero_name']}] Win Prob: {r['projected_win_prob']*100:.1f}% | Reasons: {', '.join(r['reasons'])}")
