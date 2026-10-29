"""
Dota 2 Coaching Intelligence Platform — Interactive Web Dashboard
Built with Streamlit for coaches, analysts, and serious competitive players.
Includes:
- 1. Draft Room: Live Win Probability & Hero Combination Recommender
- 2. Between-Match Coach: Empirical Percentile Diagnostics & Next-Game Tactical Briefing
- 3. Player Profiling: Playstyle Archetype Radar & TrueSkill Scouting
- 4. Synergy & Counter Matrix Explorer: 50k Match Pairwise Analytics
"""

import streamlit as st
import pandas as pd
import numpy as np

from src.models.draft_advisor import DraftAdvisor
from src.models.coach_engine import BetweenMatchCoach
from src.models.player_profiler import PlayerProfiler
from src.models.item_advisor import ItemAdvisor
from src.data.config import FEATURES_DIR
from src.data.features import HERO_ID_TO_NAME, NAME_TO_HERO_ID, ALL_HERO_IDS

st.set_page_config(
    page_title="Dota 2 Coaching Intelligence Platform",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #ff4655;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #8b9bb4;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #1a1e29;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #ff4655;
        margin-bottom: 12px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #8b9bb4;
        text-transform: uppercase;
    }
    .rec-card {
        background: #1e2433;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 10px;
    }
    .badge-win {
        background-color: #2e7d32;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-loss {
        background-color: #c62828;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .stProgress > div > div > div > div {
        background-color: #ff4655;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_all_models():
    advisor = DraftAdvisor()
    advisor.load_model()
    coach = BetweenMatchCoach()
    profiler = PlayerProfiler()
    item_adv = ItemAdvisor()
    return advisor, coach, profiler, item_adv

draft_advisor, coach_engine, player_profiler, item_advisor = load_all_models()

# Sidebar Navigation
st.sidebar.markdown("## 🎮 Navigation")
page = st.sidebar.radio(
    "Choose Module",
    [
        "⚔️ Draft Room (Pick Advisor)",
        "📋 Between-Match Coach",
        "👤 Player Profiling & Scouting",
        "🔍 Synergy & Counter Matrix",
    ],
)

hero_names_sorted = sorted([HERO_ID_TO_NAME[hid] for hid in ALL_HERO_IDS if hid in HERO_ID_TO_NAME])


# =========================================================================
# PAGE 1: DRAFT ROOM
# =========================================================================
if page == "⚔️ Draft Room (Pick Advisor)":
    st.markdown('<p class="main-title">⚔️ Draft Room & Pick Advisor</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Real-time draft win probability estimation and AI combination recommender.</p>', unsafe_allow_html=True)

    col_rad, col_center, col_dire = st.columns([5, 2, 5])

    with col_rad:
        st.markdown("### 🟢 Radiant Team")
        rad_selected = st.multiselect(
            "Select Radiant Heroes (up to 5)",
            options=hero_names_sorted,
            default=["Anti-Mage", "Crystal Maiden"],
            max_selections=5,
            key="rad_picks",
        )

    with col_dire:
        st.markdown("### 🔴 Dire Team")
        dire_selected = st.multiselect(
            "Select Dire Heroes (up to 5)",
            options=hero_names_sorted,
            default=["Juggernaut", "Pudge"],
            max_selections=5,
            key="dire_picks",
        )

    rad_ids = [NAME_TO_HERO_ID[name] for name in rad_selected if name in NAME_TO_HERO_ID]
    dire_ids = [NAME_TO_HERO_ID[name] for name in dire_selected if name in NAME_TO_HERO_ID]

    # Model Win Probability
    try:
        win_rates = draft_advisor.predict_win_probability(rad_ids, dire_ids)
        r_prob = win_rates["radiant_win_prob"] * 100
        d_prob = win_rates["dire_win_prob"] * 100
    except Exception:
        r_prob, d_prob = 50.0, 50.0

    with col_center:
        st.markdown("### ⚖️ Live Win %")
        st.metric(label="Radiant Win", value=f"{r_prob:.1f}%")
        st.metric(label="Dire Win", value=f"{d_prob:.1f}%")

    st.markdown("---")

    # Draft Advisor Recommendations Section
    st.markdown("### 🧠 AI Next-Pick Recommendations")
    target_team = st.radio("Recommend picks for:", ["Radiant", "Dire"], horizontal=True)

    target_allies = rad_ids if target_team == "Radiant" else dire_ids
    target_enemies = dire_ids if target_team == "Radiant" else rad_ids

    if len(target_allies) >= 5:
        st.info(f"{target_team} roster is already full (5 heroes picked).")
    else:
        with st.spinner("Evaluating candidate hero synergies and counter advantages..."):
            recs = draft_advisor.recommend_picks(
                ally_picks=target_allies,
                enemy_picks=target_enemies,
                target_team=target_team.lower(),
                top_n=5,
            )

        st.write(f"Showing **Top {len(recs)}** recommended picks for **{target_team}**:")

        for i, rec in enumerate(recs, 1):
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 5])
                with c1:
                    st.markdown(f"#### #{i} **{rec['hero_name']}**")
                    st.caption(f"Base Win Rate: {rec['base_win_rate']*100:.1f}%")
                with c2:
                    st.metric("Projected Win %", f"{rec['projected_win_prob']*100:.1f}%", delta=f"{rec['win_prob_gain']*100:+.1f}%")
                with c3:
                    st.metric("Synergy Score", f"{rec['synergy_score']*100:+.1f}%")
                with c4:
                    st.markdown("**Tactical Rationale:**")
                    for reason in rec["reasons"]:
                        st.markdown(f"- {reason}")
                st.markdown("<hr style='margin: 8px 0; border-color: #2d3748;'>", unsafe_allow_html=True)


# =========================================================================
# PAGE 2: BETWEEN-MATCH STRATEGIC COACH
# =========================================================================
elif page == "📋 Between-Match Coach":
    st.markdown('<p class="main-title">📋 Between-Match Strategic Coach</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Instant post-match performance audit, empirical percentile benchmarks, and next-game tactical directives.</p>', unsafe_allow_html=True)

    with st.expander("⚙️ Configure Finished Match Performance", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            hero_played = st.selectbox("Hero Played", options=hero_names_sorted, index=hero_names_sorted.index("Anti-Mage") if "Anti-Mage" in hero_names_sorted else 0)
            won_game = st.selectbox("Match Outcome", ["Loss", "Win"]) == "Win"
            opponents_faced = st.multiselect("Opponents Faced", options=hero_names_sorted, default=["Axe", "Bloodseeker", "Invoker"][:2])

        with col2:
            gpm = st.number_input("Gold Per Min (GPM)", min_value=100, max_value=1500, value=420)
            xpm = st.number_input("XP Per Min (XPM)", min_value=100, max_value=1500, value=480)
            kills = st.number_input("Kills", min_value=0, max_value=50, value=3)
            deaths = st.number_input("Deaths", min_value=0, max_value=50, value=8)
            assists = st.number_input("Assists", min_value=0, max_value=50, value=5)

        with col3:
            last_hits = st.number_input("Last Hits", min_value=0, max_value=1000, value=195)
            denies = st.number_input("Denies", min_value=0, max_value=100, value=3)
            hero_damage = st.number_input("Hero Damage", min_value=0, max_value=100000, value=9200)
            tower_damage = st.number_input("Tower Damage", min_value=0, max_value=30000, value=450)
            stuns = st.number_input("Stun Duration (sec)", min_value=0.0, max_value=300.0, value=0.0)

    hero_id = NAME_TO_HERO_ID.get(hero_played, 1)
    opp_ids = [NAME_TO_HERO_ID[name] for name in opponents_faced if name in NAME_TO_HERO_ID]

    player_stats = {
        "gold_per_min": float(gpm),
        "xp_per_min": float(xpm),
        "kills": float(kills),
        "deaths": float(deaths),
        "assists": float(assists),
        "last_hits": float(last_hits),
        "denies": float(denies),
        "hero_damage": float(hero_damage),
        "tower_damage": float(tower_damage),
        "stuns": float(stuns),
    }

    report = coach_engine.analyze_player_match(
        hero_id=hero_id,
        player_stats=player_stats,
        opponent_heroes=opp_ids,
        won_match=won_game,
    )

    st.markdown("---")

    # Diagnostic Header
    h_col1, h_col2, h_col3 = st.columns([4, 4, 4])
    with h_col1:
        outcome_badge = '<span class="badge-win">VICTORY</span>' if won_game else '<span class="badge-loss">DEFEAT</span>'
        st.markdown(f"### Performance Audit: **{hero_played}** {outcome_badge}", unsafe_allow_html=True)
    with h_col2:
        st.metric("Farming Tempo Percentile", f"{report['percentiles']['gold_per_min']:.0f}%")
    with h_col3:
        st.metric("Survivability Rating", f"{report['percentiles']['survivability']:.0f}%")

    # Radar Pillars Bar Display
    st.markdown("#### 📊 6-Pillar Empirical Benchmark Scores")
    pillar_cols = st.columns(6)
    for idx, (pillar_name, score) in enumerate(report["pillars"].items()):
        with pillar_cols[idx]:
            st.metric(label=pillar_name, value=f"{score:.0f}/100")
            st.progress(min(1.0, max(0.0, score / 100.0)))

    # Critical Leaks & Action Plan
    col_leaks, col_action = st.columns([6, 6])

    with col_leaks:
        st.markdown("### ⚠️ Critical Tactical Leaks")
        if report["critical_bottlenecks"]:
            for b in report["critical_bottlenecks"]:
                sev_color = "#e53935" if b["severity"] == "HIGH" else "#fb8c00" if b["severity"] == "MEDIUM" else "#1e88e5"
                st.markdown(f"""
                <div style="background: #1a1e29; border-left: 4px solid {sev_color}; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                    <strong style="color: {sev_color};">[{b['severity']}] {b['category']}</strong><br/>
                    <span style="color: #cbd5e1;">{b['observation']}</span><br/>
                    <em style="color: #64b5f6;">Action: {b['action']}</em>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Clean performance! No major tactical bottlenecks detected compared to hero medians.")

    with col_action:
        st.markdown("### 🎯 Next-Match Directives for Coach")
        for act in report["coach_action_plan"]:
            st.markdown(f"- 📌 **{act}**")

        if report["next_match_bans"]:
            st.markdown(f"**Recommended Bans Next Match:** `{', '.join(report['next_match_bans'])}`")

        if report["alternative_counter_picks"]:
            st.markdown("**Alternative Counter Picks:**")
            for alt in report["alternative_counter_picks"]:
                st.markdown(f"- **{alt['hero_name']}** ({alt['reason']})")


# =========================================================================
# PAGE 3: PLAYER PROFILING & SCOUTING
# =========================================================================
elif page == "👤 Player Profiling & Scouting":
    st.markdown('<p class="main-title">👤 Player Profiling & Scouting</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Scout player playstyle archetypes, TrueSkill metrics, and roster compatibility.</p>', unsafe_allow_html=True)

    col_id, col_demo = st.columns([4, 8])
    with col_id:
        acc_id = st.number_input("Enter Account ID to Scout", min_value=1, value=236579)
        scout_btn = st.button("Inspect Player Profile")

    rating_info = player_profiler.get_player_rating(int(acc_id))

    st.markdown("### 🎖️ Competitive Rating Card")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Matches", rating_info["total_matches"])
    with c2:
        st.metric("Win Rate", f"{rating_info['win_rate']*100:.1f}%")
    with c3:
        st.metric("TrueSkill μ", f"{rating_info['trueskill_mu']:.2f}")
    with c4:
        st.metric("Estimated Skill MMR", f"{rating_info['estimated_skill_rating']}")

    st.markdown("---")
    # Full Player Profile & Archetype Fingerprint
    profile = player_profiler.get_player_full_profile(int(acc_id))

    p_col1, p_col2 = st.columns([5, 7])
    with p_col1:
        st.markdown(f"#### Archetype: **{profile['archetype']}**")
        st.info(profile["archetype_summary"])
        st.markdown("**Core Career Averages:**")
        st.write(f"- Avg GPM: `{profile['averages']['gpm']}`")
        st.write(f"- Avg XPM: `{profile['averages']['xpm']}`")
        st.write(f"- Avg KDA: `{profile['averages']['kda']}`")
        st.write(f"- Avg Tower Damage: `{profile['averages']['tower_damage']:.0f}`")

    with p_col2:
        st.markdown("#### Playstyle Trait Spectrum")
        df_radar = pd.DataFrame(list(profile["radar_scores"].items()), columns=["Dimension", "Score"])
        st.bar_chart(data=df_radar.set_index("Dimension"), color="#ff4655")

    st.markdown("---")
    st.markdown("### 👥 5-Player Roster Compatibility Analyzer")
    st.markdown("Audit a competitive lineup for greedy carry farm clashes and team utility gaps.")

    r_col1, r_col2 = st.columns([8, 4])
    with r_col1:
        roster_input = st.text_input("Enter 2 to 5 Account IDs (comma-separated):", value="2701, 10307, 18680, 4390, 236579")
    with r_col2:
        audit_roster_btn = st.button("Evaluate Roster Synergy")

    try:
        r_ids = [int(x.strip()) for x in roster_input.split(",") if x.strip().isdigit()]
        if len(r_ids) >= 2:
            roster_eval = player_profiler.evaluate_roster_compatibility(r_ids)
            r_c1, r_c2 = st.columns([4, 8])
            with r_c1:
                st.metric("Roster Synergy Score", f"{roster_eval['roster_synergy_score']}/100")
                if roster_eval["resource_conflict_detected"]:
                    st.error("⚠️ Resource Conflict Detected")
                else:
                    st.success("✅ Healthy Farm Economy")
            with r_c2:
                for note in roster_eval["coach_notes"]:
                    st.markdown(f"- 📌 {note}")
    except Exception as e:
        st.warning(f"Error evaluating roster: {e}")


# =========================================================================
# PAGE 4: SYNERGY & COUNTER MATRIX EXPLORER
# =========================================================================
elif page == "🔍 Synergy & Counter Matrix":
    st.markdown('<p class="main-title">🔍 Hero Synergy & Counter Matrix Explorer</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Data-driven hero combinations and counter matchups computed across 50,000 matches.</p>', unsafe_allow_html=True)

    hero_chosen = st.selectbox("Select Hero to Analyze", options=hero_names_sorted, index=hero_names_sorted.index("Anti-Mage") if "Anti-Mage" in hero_names_sorted else 0)
    hid = NAME_TO_HERO_ID.get(hero_chosen, 1)

    s_col, c_col = st.columns(2)

    with s_col:
        st.markdown(f"### 🤝 Top Synergies with **{hero_chosen}**")
        synergy_path = FEATURES_DIR / "hero_synergy.parquet"
        if synergy_path.exists():
            df_syn = pd.read_parquet(synergy_path)
            hero_syn = df_syn[(df_syn["hero_1"] == hid) | (df_syn["hero_2"] == hid)].copy()
            hero_syn["partner_name"] = hero_syn.apply(
                lambda r: r["hero_2_name"] if r["hero_1"] == hid else r["hero_1_name"], axis=1
            )
            top_syn = hero_syn.sort_values("synergy_score", ascending=False).head(5)
            st.dataframe(
                top_syn[["partner_name", "games", "win_rate", "synergy_score"]].rename(
                    columns={
                        "partner_name": "Ally Hero",
                        "games": "Sample Games",
                        "win_rate": "Win Rate",
                        "synergy_score": "Synergy Δ",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )

    with c_col:
        st.markdown(f"### 🛡️ Hardest Counters Against **{hero_chosen}**")
        counter_path = FEATURES_DIR / "hero_counter.parquet"
        if counter_path.exists():
            df_cnt = pd.read_parquet(counter_path)
            # Enemies who beat this hero the most: opponent == hid, ordered by advantage
            counters = df_cnt[df_cnt["opponent"] == hid].sort_values("advantage", ascending=False).head(5)
            st.dataframe(
                counters[["hero_name", "games", "win_rate", "advantage"]].rename(
                    columns={
                        "hero_name": "Enemy Threat",
                        "games": "Sample Games",
                        "win_rate": "Enemy Win Rate",
                        "advantage": "Counter Advantage",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )

    st.markdown("---")
    st.markdown(f"### ⚔️ Heroes Countered by **{hero_chosen}** (Your Advantage)")
    if counter_path.exists():
        countered_by_me = df_cnt[df_cnt["hero"] == hid].sort_values("advantage", ascending=False).head(5)
        st.dataframe(
            countered_by_me[["opponent_name", "games", "win_rate", "advantage"]].rename(
                columns={
                    "opponent_name": "Victim Hero",
                    "games": "Sample Games",
                    "win_rate": "Your Win Rate",
                    "advantage": "Your Advantage",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
