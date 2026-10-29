"""
Context-Aware Itemization Advisor (Model 5):
Analyzes optimal item builds, win-rate correlations, timing benchmarks,
and recommends situational counter-items conditioned on enemy lineup threats.
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from src.data.config import RAW_DATA_DIR, FEATURES_DIR
from src.data.loaders import load_item_names, get_item_dict
from src.data.features import HERO_ID_TO_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Tactical situational counters mapping (Enemy Threat Hero IDs -> Recommended Counter Item Names)
SITUATIONAL_COUNTERS = {
    # High Evasion / Blind (PA: 44, Windranger: 21, Riki: 32, Brewmaster: 78)
    "evasion_threats": {
        "heroes": [44, 21, 32, 78],
        "recommended_items": [
            {"item_name": "Monkey King Bar", "timing_min": 25, "reason": "Bypasses evasion and blind debuffs with True Strike."},
            {"item_name": "Bloodthorn / Orchid", "timing_min": 24, "reason": "Applies silence and True Strike on the afflicted target."},
        ]
    },
    # Heavy Magic Burst & Crowd Control (Lion: 26, Lina: 25, Shadow Shaman: 27, Storm Spirit: 17, Invoker: 74)
    "magic_cc_threats": {
        "heroes": [26, 25, 27, 17, 74],
        "recommended_items": [
            {"item_name": "Black King Bar", "timing_min": 20, "reason": "Provides spell immunity to survive burst combos and disables."},
            {"item_name": "Lotus Orb", "timing_min": 22, "reason": "Dispel debuffs and reflects targeted spells back to enemy casters."},
        ]
    },
    # High Armor / Massive Tank (Centaur: 96, Pudge: 14, Axe: 2, Bristleback: 99, Tidehunter: 29)
    "tank_threats": {
        "heroes": [96, 14, 2, 99, 29],
        "recommended_items": [
            {"item_name": "Eye of Skadi", "timing_min": 28, "reason": "Slows movement and reduces healing/regeneration by 40%."},
            {"item_name": "Desolator", "timing_min": 18, "reason": "Reduces target armor by 6 to quickly shred tanky frontline."},
        ]
    },
    # Physical Right-Click Hyper Carries (Sven: 18, Ursa: 70, Phantom Assassin: 44, Juggernaut: 8, Slardar: 28)
    "physical_carry_threats": {
        "heroes": [18, 70, 44, 8, 28],
        "recommended_items": [
            {"item_name": "Heaven's Halberd", "timing_min": 20, "reason": "Disarms physical carries for up to 5 seconds."},
            {"item_name": "Shiva's Guard / Assault Cuirass", "timing_min": 28, "reason": "Aura armor boost and attack speed reduction."},
        ]
    },
    # High Regeneration & Lifesteal (Necrophos: 36, Alchemist: 73, Huskar: 59, Slark: 93)
    "healing_regen_threats": {
        "heroes": [36, 73, 59, 93],
        "recommended_items": [
            {"item_name": "Spirit Vessel", "timing_min": 16, "reason": "Reduces target health restoration and healing by 45%."},
            {"item_name": "Eye of Skadi", "timing_min": 28, "reason": "Passive attacks reduce target healing and lifesteal by 40%."},
        ]
    },
    # Swarm Illusions & Clones (Phantom Lancer: 12, Chaos Knight: 81, Naga Siren: 89, Terrorblade: 109)
    "illusion_threats": {
        "heroes": [12, 81, 89, 109],
        "recommended_items": [
            {"item_name": "Mjollnir / Maelstrom", "timing_min": 18, "reason": "Chain lightning bounces shred illusion swarms efficiently."},
            {"item_name": "Battle Fury / Radiance", "timing_min": 16, "reason": "Continuous area-of-effect damage clears illusions and summons."},
        ]
    },
}

# Standard Core Item Timing Benchmarks
CORE_ITEM_TIMINGS = {
    "black_king_bar": {"target_min": 21, "gold": 3975, "priority": "Essential vs Magic/CC"},
    "blink": {"target_min": 14, "gold": 2250, "priority": "Initiation Power Spike"},
    "manta": {"target_min": 22, "gold": 4950, "priority": "Dispel & Split-push"},
    "ultimate_scepter": {"target_min": 20, "gold": 4200, "priority": "Hero Ability Power Spike"},
    "desolator": {"target_min": 18, "gold": 3500, "priority": "Early Armor Reduction & Push"},
    "orchid": {"target_min": 17, "gold": 4075, "priority": "Pick-off & Silence Tempo"},
}


class ItemAdvisor:
    def __init__(self):
        self.item_dict = get_item_dict()

    def recommend_situational_items(self, hero_id: int, enemy_hero_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Recommends counter items based on identified threats in the enemy draft.
        """
        recommendations = []
        enemy_set = set(enemy_hero_ids)

        for threat_cat, threat_info in SITUATIONAL_COUNTERS.items():
            matching_threats = [h for h in threat_info["heroes"] if h in enemy_set]
            if matching_threats:
                threat_names = [HERO_ID_TO_NAME.get(h, f"Hero {h}") for h in matching_threats]
                for rec in threat_info["recommended_items"]:
                    recommendations.append({
                        "item_name": rec["item_name"],
                        "target_timing_minutes": rec["timing_min"],
                        "threat_category": threat_cat.replace("_", " ").title(),
                        "countering_heroes": threat_names,
                        "strategic_rationale": rec["reason"],
                    })

        return recommendations

    def get_timing_benchmarks(self) -> Dict[str, Any]:
        """Returns standard timing benchmarks for core game-deciding items."""
        return CORE_ITEM_TIMINGS
