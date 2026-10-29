"""
Dota 2 Coaching Intelligence Platform — Unified Service Orchestrator
Verifies dataset artifacts, checks model files, and launches services.
"""

import os
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def check_environment():
    print("=" * 65)
    print("  AEGIS DOTA 2 COACHING INTELLIGENCE PLATFORM — SYSTEM VERIFY")
    print("=" * 65)

    raw_dir = ROOT_DIR / "data" / "raw" if (ROOT_DIR / "data" / "raw").exists() else ROOT_DIR
    player_ratings_path = raw_dir / "player_ratings.csv" if (raw_dir / "player_ratings.csv").exists() else ROOT_DIR / "player_ratings.csv"
    hero_names_path = raw_dir / "hero_names.csv" if (raw_dir / "hero_names.csv").exists() else ROOT_DIR / "hero_names.csv"

    required_artifacts = [
        ROOT_DIR / "models" / "draft_xgb_model.pkl",
        ROOT_DIR / "models" / "draft_model_meta.json",
        ROOT_DIR / "data" / "features" / "hero_benchmarks.parquet",
        ROOT_DIR / "data" / "features" / "hero_synergy.parquet",
        ROOT_DIR / "data" / "features" / "hero_counter.parquet",
        ROOT_DIR / "data" / "features" / "hero_stats.parquet",
        ROOT_DIR / "data" / "features" / "player_matches.parquet",
        player_ratings_path,
        hero_names_path,
    ]

    all_ok = True
    for p in required_artifacts:
        if p.exists():
            size_mb = p.stat().st_size / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB" if size_mb >= 1.0 else f"{p.stat().st_size / 1024:.1f} KB"
            print(f"  [OK] {p.name:<30} ({size_str})")
        else:
            print(f"  [MISSING] {p.name}")
            all_ok = False

    print("-" * 65)
    return all_ok

def main():
    if not check_environment():
        print("Warning: Some feature artifacts were missing.")
        sys.exit(1)

    print("\nSelect platform service to launch:")
    print("  1) Run Automated Test Suite (21 tests)")
    print("  2) Start FastAPI REST Backend (port 8000)")
    print("  3) Start Streamlit Analytics Dashboard (port 8501)")
    print("  4) Build & Launch React Frontend (Vite port 5173)")
    print("  5) Start Full Stack (FastAPI + Vite Frontend)")
    print("  6) Launch Docker Compose Production Stack (FastAPI + Nginx React)")
    
    choice = sys.argv[1] if len(sys.argv) > 1 else input("\nEnter choice [1-6] (default: 1): ").strip() or "1"

    if choice == "1":
        subprocess.run([sys.executable, str(ROOT_DIR / "tests" / "test_platform.py")])
    elif choice == "2":
        print("\nStarting FastAPI REST Server on http://localhost:8000 (Docs: http://localhost:8000/docs)...")
        subprocess.run([sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
    elif choice == "3":
        print("\nStarting Streamlit Dashboard on http://localhost:8501...")
        subprocess.run(["streamlit", "run", str(ROOT_DIR / "src" / "dashboard" / "app.py"), "--server.port", "8501"])
    elif choice == "4":
        frontend_dir = ROOT_DIR / "frontend"
        print("\nStarting Vite React Frontend on http://localhost:5173...")
        cmd = "npm.cmd" if os.name == "nt" else "npm"
        subprocess.run([cmd, "run", "dev"], cwd=frontend_dir)
    elif choice == "5":
        print("\nLaunching Full Stack (FastAPI backend + Vite frontend)...")
        cmd = "npm.cmd" if os.name == "nt" else "npm"
        backend_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"])
        try:
            subprocess.run([cmd, "run", "dev"], cwd=ROOT_DIR / "frontend")
        finally:
            backend_proc.terminate()
    elif choice == "6":
        print("\nBuilding & Launching Docker Compose Stack (Backend + Frontend Nginx)...")
        subprocess.run(["docker", "compose", "up", "-d", "--build"])
        print("\nStack launched successfully!")
        print("  - Web Frontend: http://localhost:80")
        print("  - REST Backend Docs: http://localhost:8000/docs")
        print("  - Health Probe: http://localhost:8000/health")
    else:
        print(f"Unknown choice: {choice}")

if __name__ == "__main__":
    main()
