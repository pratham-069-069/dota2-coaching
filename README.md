# 🎮 Dota 2 Coaching Intelligence Platform

An end-to-end Data Science and Machine Learning platform built for **coaches, pro players, and competitive teams** using 50,000 matches (~1.4 GB) of competitive Dota 2 data.

---

## 🌟 Core Features & Modules

### 1. ⚔️ Draft Room & Hero Pick Advisor (Model 1)
- **Trained on 50,000 matches** with XGBoost classifier (Test AUC-ROC: **0.6378**, Accuracy: **60%**).
- **Live Win Probability**: Dynamically predicts Radiant and Dire win probabilities for partial and complete 5v5 drafts.
- **AI Next-Pick Recommender**:
  - Evaluates all available heroes based on projected win probability gain, allied hero synergies, and enemy counter matchups.
  - Generates concrete, natural-language tactical explanations (e.g., *"+4.3% combo with Anti-Mage, +3.1% counter vs Juggernaut"*).

### 2. 📋 Between-Match Strategic Coach (Model 3)
- Designed specifically for the **5-10 minute window between competitive matches**.
- **Empirical Percentile Benchmarking**: Compares the player's match performance against empirical distributions calculated across 500,000 player records for that specific hero.
- **6-Pillar Gameplay Evaluation**: Farming Tempo, Teamfight Impact, Objective Focus, Laning Precision, Crowd Control, and Survivability.
- **Critical Tactical Leaks**: Pinpoints severe weaknesses with actionable remedies (e.g., Farming Deficit, High Mortality Rate, Low Objective Conversion).
- **Next-Game Tactical Directives**: High-priority bans to target enemy comfort heroes, pocket counter-picks, and strategic adjustments.

### 3. 👤 Player Profiling & Scouting (Model 4)
- **TrueSkill Metrics**: Integrates TrueSkill $\mu$ and $\sigma$ from `player_ratings.csv` to estimate competitive MMR and win consistency.
- **Playstyle Archetype Classification**: Categorizes players into archetypes (*Greedy Hard Carry, Tempo Initiator, Siege Specialist, Tactical Playmaker, Adaptive Core*).
- **Roster Compatibility Analyzer**: Detects resource conflicts (multiple farm-heavy cores competing for jungle camps) and team utility gaps.

### 4. 🔍 Hero Synergy & Counter Matrix Explorer
- Precomputed **pairwise synergy scores** and **counter advantages** across all 112 heroes.
- Search any hero to inspect their top 5 allied synergy partners, hardest counters, and optimal item timing benchmarks.

---

## 🚀 Quickstart

### 1. Requirements
Ensure Python 3.10+ is installed:
```bash
pip install pandas numpy scikit-learn xgboost streamlit fastapi uvicorn pyarrow
```

### 2. Feature Extraction & Model Training (Already Precomputed)
If you wish to re-extract features or retrain the model from raw CSVs:
```bash
# Compute hero win rates, synergy matrices, and counter matrices
python -m src.data.features

# Compute empirical quantile benchmarks per hero
python -m src.data.benchmarks

# Train the Draft Advisor XGBoost model
python -m src.models.draft_advisor
```

### 3. Launch the Modern React Web App (Recommended)
The React application is running live at:
👉 **[http://localhost:5173](http://localhost:5173)**

To start the React frontend anytime:
```bash
cd frontend
npm run dev
```

### 4. Launch the Streamlit Dashboard (Alternative)
The Streamlit dashboard is also available at:
👉 **[http://localhost:8501](http://localhost:8501)**

To launch it manually anytime:
```bash
streamlit run src/dashboard/app.py --server.port 8501
```

### 5. Launch the REST API
To start the FastAPI backend:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger docs: **`http://localhost:8000/docs`**

### 6. Run Automated Test Suite
To run all 21 automated platform and API tests:
```bash
python tests/test_platform.py
```

### 7. 🐳 DevOps, Docker & CI/CD Pipeline
The repository features complete enterprise DevOps automation:
- **Continuous Integration (CI):** Automated linting (`flake8`, `oxlint`), 21-test ML & API suite, and Docker build sanity checks on every pull request and push.
- **Continuous Deployment (CD):** GitHub Actions and GitLab CI/CD pipelines that build, test, and automatically reflect code changes on the production server without manual intervention.
- **Microservices Orchestration:** Multi-stage lean Dockerfiles and `docker-compose.yml` with reverse proxy (Nginx) and Watchtower auto-updater.

To run the entire production-ready platform in containers:
```bash
docker compose up -d --build
```
- **Web Application:** [http://localhost](http://localhost) (Port 80)
- **FastAPI REST Engine:** [http://localhost:8000/docs](http://localhost:8000/docs) (Port 8000)
- **Automated Healthcheck:** [http://localhost:8000/health](http://localhost:8000/health)

📘 For full CI/CD pipeline setup, GitHub Secrets, GitLab CI variables, and zero-downtime server setup, see **[DEVOPS.md](DEVOPS.md)**.

---

## 📁 Repository Structure

```
e:\Dota2\
├── data/
│   ├── features/               # Precomputed parquet & JSON feature stores
│   │   ├── hero_benchmarks.parquet
│   │   ├── hero_counter.parquet
│   │   ├── hero_stats.parquet
│   │   ├── hero_synergy.parquet
│   │   ├── match_drafts.parquet
│   │   └── player_matches.parquet
│   └── processed/
│
├── frontend/                   # Modern React (Vite) Glassmorphism Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── DraftRoom.jsx          # Live drafts, bans & situational items
│   │   │   ├── BetweenMatchCoach.jsx  # 6-pillar audit & 1-click DB match loader
│   │   │   ├── PlayerScout.jsx        # TrueSkill scouting & 5-player roster synergy
│   │   │   └── MatrixExplorer.jsx     # Dynamic 112-hero pairwise matrices
│   │   └── services/api.js
│
├── models/
│   ├── draft_xgb_model.pkl     # Trained XGBoost Draft Model artifact
│   └── draft_model_meta.json   # Model evaluation metrics & metadata
│
├── src/
│   ├── api/
│   │   └── main.py             # FastAPI REST endpoints
│   ├── dashboard/
│   │   └── app.py              # Streamlit interactive multi-page dashboard
│   ├── data/
│   │   ├── config.py           # Paths, roles, and competitive game modes
│   │   ├── loaders.py          # Data ingestion utilities
│   │   ├── features.py         # Synergy, counter, and draft vector extraction
│   │   └── benchmarks.py       # Empirical hero quantile computation
│   └── models/
│       ├── draft_advisor.py    # Model 1: Draft Advisor & Recommender
│       ├── coach_engine.py     # Model 3: Between-Match Strategic Coach
│       ├── player_profiler.py  # Model 4: Player Profiler & Scouting
│       └── item_advisor.py     # Model 5: Situational Item Advisor
│
├── tests/
│   └── test_platform.py        # Automated test suite (19 tests)
│
└── README.md
```
