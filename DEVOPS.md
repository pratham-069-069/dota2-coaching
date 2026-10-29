# 🚀 Dota 2 Coaching Intelligence Platform — DevOps & CI/CD Architecture

> **Complete DevOps Engineering Guide:** Continuous Integration, Automated Testing, Multi-Stage Containerization, GitHub Actions & GitLab CI/CD, and Zero-Intervention Server Auto-Deployment.

---

## 📑 Table of Contents
1. [Architectural Overview & Workflow Diagram](#1-architectural-overview--workflow-diagram)
2. [Automated CI/CD Pipeline Lifecycle](#2-automated-cicd-pipeline-lifecycle)
3. [Zero-Intervention Automatic Server Reflection](#3-zero-intervention-automatic-server-reflection)
4. [GitHub Actions CI/CD Setup](#4-github-actions-cicd-setup)
5. [GitLab CI/CD Setup](#5-gitlab-cicd-setup)
6. [Containerization & Orchestration (Docker & Compose)](#6-containerization--orchestration-docker--compose)
7. [Production Server Initialization & Deployment Script](#7-production-server-initialization--deployment-script)
8. [Automated Health Checks & Zero-Downtime Rollback](#8-automated-health-checks--zero-downtime-rollback)
9. [Local Developer Environment (Hot-Reload)](#9-local-developer-environment-hot-reload)

---

## 1. Architectural Overview & Workflow Diagram

Whenever any developer pushes code or merges a Pull Request into `master` or `main`, the DevOps automation triggers end-to-end:

```mermaid
flowchart TD
    subgraph Developer["💻 Developer Workstation"]
        A[Git Commit & Push] -->|Push to master/main| B(Remote Repository)
    end

    subgraph CI["🧪 Continuous Integration (GitHub Actions / GitLab CI)"]
        B --> C{CI Pipeline Trigger}
        C --> D1[Backend Lint & Flake8]
        C --> D2[Frontend Oxlint & Vite Build]
        D1 --> E1[21-Test Automated ML Suite]
        D2 --> E2[Verify Production Bundles]
        E1 & E2 --> F[Build Multi-Stage Docker Images]
        F --> G[Push to Container Registry - GHCR / GitLab Registry]
    end

    subgraph CD["🚀 Continuous Deployment (Zero Manual Intervention)"]
        G --> H1[Option 1: CD Workflow SSH Push]
        G --> H2[Option 2: GitOps Watchtower Polling]
        G --> H3[Option 3: Webhook Auto-Deployer]
    end

    subgraph ProductionServer["☁️ Production Server / Cloud VPS"]
        H1 & H2 & H3 --> I[Docker Compose Pull & Rolling Update]
        I --> J[Run Health Check on /health]
        J -->|200 OK| K[✅ Live Production Traffic Switched]
        J -->|Failure| L[⚠️ Automatic Rollback to Last Healthy Image]
    end
```

---

## 2. Automated CI/CD Pipeline Lifecycle

The platform includes two enterprise-grade CI/CD pipeline definitions:
- **GitHub Actions:** Located in [`.github/workflows/ci.yml`](file:///e:/Dota2/.github/workflows/ci.yml) and [`.github/workflows/cd.yml`](file:///e:/Dota2/.github/workflows/cd.yml).
- **GitLab CI/CD:** Located in [`.gitlab-ci.yml`](file:///e:/Dota2/.gitlab-ci.yml).

### Pipeline Stages

| Stage | Tool | Description | Failure Action |
| :--- | :--- | :--- | :--- |
| **Linting** | `flake8` + `oxlint` | Static code analysis, syntax checks, undefined references. | Pipeline aborts immediately. |
| **Testing** | `python tests/test_platform.py` | 21 comprehensive integration tests (Draft ML, Coach benchmarks, TrueSkill, Roster, REST API). | Halts build; prevents bad models from reaching production. |
| **Build Check** | `vite build` | Compiles React components, verifies CSS/JS bundle integrity. | Halts build if frontend fails compilation. |
| **Container Build** | `docker buildx` | Builds multi-stage slim images for FastAPI backend & Nginx frontend. | Caches layers via GHA cache. |
| **Push** | `GHCR` / `GitLab Registry` | Tags image with git commit SHA and `latest`. | Stored in secure private/public registry. |
| **Deploy** | `scripts/deploy.sh` | Pulls new images onto server, updates containers, tests `/health`. | Triggers automatic rollback if `/health` fails. |

---

## 3. Zero-Intervention Automatic Server Reflection

To satisfy the requirement that **as soon as you change code, it automatically reflects on the server without manual intervention**, you can choose between two mechanisms:

### Method A: Automated SSH Push via GitHub Actions (Recommended)
1. You push a commit to `master`.
2. GitHub Actions runs CI (tests, linters).
3. GitHub Actions builds the Docker images and pushes them to GitHub Container Registry (`ghcr.io`).
4. GitHub Actions SSHs into your cloud server using the secret `SSH_PRIVATE_KEY`.
5. It executes `docker compose pull && docker compose up -d`.
6. It polls `http://localhost:8000/health` until the machine learning models are verified loaded.
7. Total time from `git push` to live on server: **~90 to 120 seconds**.

### Method B: GitOps Pull via Watchtower (Zero Configuration on GitHub)
If you don't want to manage SSH keys inside GitHub Secrets:
1. Your server runs `watchtower` as configured in [`docker-compose.yml`](file:///e:/Dota2/docker-compose.yml):
   ```bash
   docker compose --profile autodeploy up -d
   ```
2. Watchtower silently polls the container registry every 60 seconds (`WATCHTOWER_INTERVAL=60`).
3. Whenever GitHub Actions finishes building a new image, Watchtower detects the new image digest on GHCR.
4. Watchtower gracefully restarts the running container with the new image, with zero manual command execution!

### Method C: Webhook Auto-Deployer
For private bare-metal servers behind a firewall:
- Run the included lightweight webhook daemon:
  ```bash
  python scripts/webhook_deployer.py
  ```
- Add the webhook URL `http://your-server-ip:9000/` to your GitHub / GitLab repository settings under **Webhooks**. Every `git push` immediately pings your server and triggers `scripts/deploy.sh`!

---

## 4. GitHub Actions CI/CD Setup

### Step 1: Push Code to GitHub
```bash
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin master
```

### Step 2: Configure GitHub Repository Secrets
Navigate to **Settings** > **Secrets and variables** > **Actions** and add:

| Secret Name | Value Example | Purpose |
| :--- | :--- | :--- |
| `SERVER_HOST` | `142.93.100.50` (or your domain) | Production server IP or hostname. |
| `SERVER_USER` | `ubuntu` (or `root`) | SSH username on production server. |
| `SSH_PRIVATE_KEY` | `-----BEGIN OPENSSH PRIVATE KEY...` | Private SSH key matching `~/.ssh/authorized_keys` on server. |
| `SERVER_PORT` | `22` (default) | Custom SSH port (optional). |
| `SERVER_DEPLOY_PATH` | `/opt/dota2-coaching` | Project root directory on the server. |

*(Note: `GITHUB_TOKEN` is automatically created by GitHub Actions with permissions to push to `ghcr.io`)*.

---

## 5. GitLab CI/CD Setup

If hosting on GitLab:

### Step 1: Configure GitLab CI/CD Variables
Navigate to **Settings** > **CI/CD** > **Variables** and add:
- `SERVER_HOST`: Production IP address.
- `SERVER_USER`: SSH user (e.g., `ubuntu`).
- `SSH_PRIVATE_KEY`: Private SSH Key.
- `SERVER_DEPLOY_PATH`: `/opt/dota2-coaching`.

GitLab's native registry `$CI_REGISTRY` is automatically configured by [`.gitlab-ci.yml`](file:///e:/Dota2/.gitlab-ci.yml).

---

## 6. Containerization & Orchestration (Docker & Compose)

### Docker Architecture
- **Backend ([`Dockerfile.backend`](file:///e:/Dota2/Dockerfile.backend)):**
  - Base: `python:3.11-slim` with `libgomp1` for XGBoost OpenMP acceleration.
  - Multi-stage build with non-root user `appuser` (UID 1001) for security compliance.
  - Automated Docker `HEALTHCHECK` against `http://localhost:8000/health`.
  - Context size optimized using [`.dockerignore`](file:///e:/Dota2/.dockerignore) (ignores >1.4 GB raw training data, keeping image build transfer <60 MB).

- **Frontend ([`Dockerfile.frontend`](file:///e:/Dota2/Dockerfile.frontend)):**
  - Stage 1: `node:20-alpine` builds optimized static bundles (`npm run build`).
  - Stage 2: `nginx:alpine-slim` serves static files with Gzip compression and security headers.
  - Reverse Proxy ([`nginx/default.conf`](file:///e:/Dota2/nginx/default.conf)): Routes `/api/*` and direct API paths to the backend service.

- **Orchestration ([`docker-compose.yml`](file:///e:/Dota2/docker-compose.yml)):**
  - Manages `backend`, `frontend`, and optional `watchtower` on a shared bridge network `dota2-network`.
  - Depends-on condition: `frontend` starts only after `backend` reports `service_healthy`.

---

## 7. Production Server Initialization & Deployment Script

### Initial Server Setup (One-Time Execution on Server)
On your Ubuntu/Debian server:
```bash
# 1. Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# 2. Clone repository to /opt/dota2-coaching
sudo mkdir -p /opt/dota2-coaching
sudo chown -R $USER:$USER /opt/dota2-coaching
git clone https://github.com/<your-username>/<your-repo-name>.git /opt/dota2-coaching
cd /opt/dota2-coaching

# 3. Create production environment file
cp .env.example .env

# 4. Launch with automated deployment script
chmod +x scripts/deploy.sh scripts/healthcheck.sh
./scripts/deploy.sh
```

---

## 8. Automated Health Checks & Zero-Downtime Rollback

The automated deployment script [`scripts/deploy.sh`](file:///e:/Dota2/scripts/deploy.sh):
1. Pulls the latest container images.
2. Performs rolling update (`docker compose up -d --remove-orphans`).
3. Probes the backend `/health` endpoint up to 15 times (every 5s).
4. Verifies all model components:
   ```json
   {
     "status": "healthy",
     "models": {
       "draft_advisor_loaded": true,
       "hero_benchmarks_loaded": true,
       "player_profiler_loaded": true,
       "item_advisor_loaded": true
     }
   }
   ```
5. **Rollback guarantee:** If health checks fail, the script immediately prints the last 40 lines of container logs, triggers `docker compose restart`, and exits with an error code to notify your pipeline.

---

## 9. Local Developer Environment (Hot-Reload)

To run the full stack locally with hot-reloading for rapid development:

```bash
# Launch both backend (with uvicorn --reload) and frontend (Vite dev)
docker compose -f docker-compose.dev.yml up --build
```

- **Frontend:** http://localhost:5173
- **FastAPI Backend & Interactive Swagger Docs:** http://localhost:8000/docs
- Changes made to files in `src/` or `frontend/src/` automatically reload in the browser instantly!

