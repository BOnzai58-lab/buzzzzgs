# 🎯 BugHunter AI

<p align="center">
  <strong>Autonomous Bug Bounty Reconnaissance & Vulnerability Analysis Platform</strong><br>
  <em>AI-powered · Deterministic Scope Enforcement · Process Cancellation · Verification Engine · Kali Linux Native</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/TailwindCSS-v4-38B2AC?logo=tailwindcss&logoColor=white" alt="Tailwind v4" />
  <img src="https://img.shields.io/badge/Kali_Linux-Ready-557C94?logo=kalilinux&logoColor=white" alt="Kali Linux Ready" />
  <img src="https://img.shields.io/badge/Tests-46%20Passed%20(100%25)-brightgreen" alt="Tests 46 Passed" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License" />
</p>

---

## 🚀 Latest Update: Safety, Verification & Reliability Hardening

In response to the comprehensive Technical Review Report, BugHunter AI has completed **Phase 1 through Phase 4** hardening:

- **🛡️ Strict Wildcard & Scope Semantics (§1.1)**: Wildcard rules like `*.example.com` strictly encompass subdomains (`api.example.com`, `admin.sub.example.com`). Root apex domains (`example.com`) are **not** inferred to be in-scope unless explicitly listed.
- **🚫 Automated SSRF & Cloud Metadata Defense (§1.1)**: Target validation deterministically blocks loopbacks (`127.0.0.1`), RFC1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and AWS/GCP/Azure instance metadata (`169.254.169.254`) unless explicitly covered by a dedicated CIDR rule.
- **🔄 HTTP 3xx Redirect Scope Validation (§1.1)**: Every redirect hop is inspected in real-time. If an asset redirects out-of-scope or toward private metadata, the chain is safely terminated.
- **🛑 Process-Level Task Cancellation (§1.2)**: New `ProcessTracker` registers child tool processes (`subfinder`, `httpx`, `katana`, `nuclei`) and executes deterministic OS-level process tree termination (`taskkill /F /T` on Windows, `SIGKILL` process groups on Linux) whenever a scan is stopped.
- **🔍 Verification Engine & Status Gating (§1.3, §4.4)**: New `VerificationEngine` performs safe, non-destructive HTTP verification checks with reproducible `curl` generation and SHA-256 evidence hashing. Transitioning findings to `verified` requires:
  1. An impact explanation note ($\ge$ 10 chars).
  2. Confirmed target scope revalidation.
  3. A reproducible test (`curl` command or reproduction steps).
  4. Raw HTTP request/response evidence (preventing raw scanner labels from acting as verified bugs).
  5. Human analyst authorization.
- **🔐 WebSocket Ownership Authorization (§1.4)**: Real-time scan log subscriptions now validate JWTs and enforce user-to-scan ownership or admin roles.
- **📄 Evidence-Grounded Reporting (§1.5, §4.6)**: Reports are strictly generated as **DRAFT — HUMAN REVIEW REQUIRED** with authentic HTTP artifacts, CVSS v3.1 calculations (never fabricated), and complete researcher checklists.
- **🐧 Resilient Linux/Kali Setup (§2.1)**: Setup scripts auto-detect and recreate Windows-copied virtual environments, pin Go security tools to verified versions, and execute functional self-tests.
- **🧪 46-Test Automated Suite (§2.4, §6)**: Built `run_tests.py` covering scope validation, process tracking, verification engine, and report generation with **100% test pass rate**.

---

## 📑 Table of Contents
- [🌟 Key Capabilities](#-key-capabilities)
- [🖥️ Web Control Dashboard (14 Pages)](#️-web-control-dashboard-14-pages)
- [📦 Batch Hunting Center (§10)](#-batch-hunting-center-10)
- [🛡️ Verification Engine & Evidence Collection](#️-verification-engine--evidence-collection)
- [🛠️ Linux Native Tool Manager](#️-linux-native-tool-manager)
- [🔒 Safety & Scope Controls](#-safety--scope-controls)
- [🤖 AI Engine Configuration](#-ai-engine-configuration)
- [🚀 Quick Start & Setup Guides](#-quick-start--setup-guides)
  - [Mode 1: Windows Local Dev (No Docker Required)](#mode-1-windows-local-development-no-docker-needed)
  - [Mode 2: Kali Linux / Ubuntu (VirtualBox or Bare Metal)](#mode-2-kali-linux--ubuntu-virtualbox-or-bare-metal)
  - [Mode 3: Production Docker Deployment](#mode-3-docker-compose-production)
- [🧪 Running the Automated Test Suite](#-running-the-automated-test-suite)
- [🔄 How to Push Changes to GitHub](#-how-to-push-changes-to-github)
- [⚖️ Ethical Disclosure & Legal Disclaimer](#️-ethical-disclosure--legal-disclaimer)

---

## 🌟 Key Capabilities

- **🚀 Autonomous Pipeline**: Orchestrates discovery from passive subdomain resolution, active probing, and endpoint spidering through to automated non-destructive vulnerability assessment.
- **🛡️ 100% Deterministic Scope Validation**: Scope decisions are executed strictly in pure Python (`ipaddress` and RFC-compliant domain matching). **AI is never permitted to decide or validate scope.** Exclusions always take precedence.
- **📦 Batch Hunting & Queue System (§10)**: Import and process 100+ authorized targets simultaneously via TXT, CSV, JSON, or manual multiline input through a persistent background job queue.
- **🛑 Real Process Kill Stop**: Stopping a scan terminates the underlying tool process immediately via OS process trees, rather than merely flipping a UI flag.
- **🐧 Native Linux Tool Manager**: Fully automated detection, installation, version checking, and execution of 12 industry-standard security tools natively inside Linux / Kali Linux.
- **🤖 Universal AI Triage Engine**: Direct integration with OpenAI-compatible APIs (OpenAI `gpt-4o-mini`, OpenRouter, Groq, or 100% offline local Ollama). Performs deduplication, CVSS calculation, and reproduction step drafting.
- **📊 Professional Reporting**: One-click generation of HackerOne- and Bugcrowd-compliant vulnerability disclosure reports in Markdown, PDF, JSON, CSV, and HTML formats.

---

## 🖥️ Web Control Dashboard (14 Pages)

BugHunter AI provides a dark-themed responsive operations center built with React 19, TypeScript, and Tailwind CSS v4:

| # | Page | Route | Description |
|---|---|---|---|
| 1 | **Overview** | `/` | Executive telemetry, active programs, live host stats, and severity donut chart. |
| 2 | **Programs** | `/programs` | Bug bounty engagement manager with scope rules, allowed HTTP methods, and rate limits. |
| 3 | **Batch Hunting** | `/batch-hunting` | Bulk target submission, pre-queue validation, queue controls, and batch summary reports. |
| 4 | **Reconnaissance** | `/recon` | Manual scan launcher for subdomains, DNS, probing, and crawling with live WebSocket logs. |
| 5 | **Assets** | `/assets` | Searchable asset inventory with in-scope / out-of-scope status tags. |
| 6 | **Live Hosts** | `/live-hosts` | Discovered HTTP/HTTPS hosts with response codes, page titles, and tech stacks. |
| 7 | **Endpoints** | `/endpoints` | Crawled URLs, endpoints, parameters, and HTTP verbs. |
| 8 | **Findings** | `/findings` | Vulnerability triage table with severity badges, status workflows, and AI triggers. |
| 9 | **AI Analysis** | `/ai-analysis` | Detailed LLM triage breakdown, root cause, CVSS vector, and suggested remediation. |
| 10 | **Reports** | `/reports` | Multi-format vulnerability report viewer, editor, and PDF exporter. |
| 11 | **Scan History** | `/scan-history` | Immutable log of all previous scans, execution durations, and exit statuses. |
| 12 | **Tool Manager** | `/tools` | Host detection, real-time tool statuses, bulk installer, and streaming terminal logs. |
| 13 | **Approvals** | `/approvals` | **Human-in-the-loop gate**: Manual review, approval, or rejection before active verification. |
| 14 | **Settings** | `/settings` | AI provider configuration, password manager, and platform metadata. |

---

## 📦 Batch Hunting Center (§10)

The **Batch Hunting Center** enables high-volume authorized security assessments:

### 1. Multi-Format Target Import
- **Plain Text (`.txt`)**: Paste or upload raw target lists (one per line, auto-ignoring comments).
- **Structured CSV (`.csv`)**: Maps `target`, `program`, `authorization_reference`, `priority`, `testing_profile`, `notes`.
- **JSON (`.json`)**: Accepts target arrays or structured configuration payloads.
- **Intra-Batch & Cross-Batch Deduplication**: Detects existing assessments to prevent repeated traffic.

### 2. Pre-Queue Authorization Engine
Before any target enters the execution queue, it must pass individual validation:
- **`VALIDATED`**: In-scope and confirmed against an active program.
- **`EXCLUDED`**: Matches an explicit exclusion rule (automatically blocked).
- **`OUT_OF_SCOPE`**: Target not authorized in scope definitions.
- **`POLICY_EXPIRED`**: Engagement window closed or program deactivated.

### 3. Persistent Queue & Rate Limiting
- Token-bucket rate limiting enforces program-specific requests-per-second (RPS).
- Supports **Local Mode** (work persists across restarts) and **Server Mode** (background execution continues even if your browser is closed).

---

## 🛡️ Verification Engine & Evidence Collection

Raw scanner alerts are treated as **unverified candidates** until substantiated:

1. **Non-Destructive Testing**: `VerificationEngine` re-validates targets using safe HTTP requests (GET/HEAD) with strict redirect-hop scope gating.
2. **Reproducible `curl` Commands**: Every finding stores copy-paste ready `curl` commands formatted with all relevant headers and data.
3. **Cryptographic Hashes**: SHA-256 hashes are calculated and stored for all raw request and response payloads to ensure evidence integrity.
4. **Human Verification**: Transitioning a finding to `verified` requires human analyst review, an impact note ($\ge$ 10 chars), confirmed scope, and real HTTP evidence.

---

## 🛠️ Linux Native Tool Manager

BugHunter AI manages and verifies **12 core security tools** directly from official upstream sources with pinned versions for build reproducibility:

| Tool | Category | Verified Version | Installation Command |
|---|---|---|---|
| **`subfinder`** | Passive Subdomains | `v2.6.8` | `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.6.8` |
| **`dnsx`** | DNS Toolkit | `v1.1.7` | `go install github.com/projectdiscovery/dnsx/cmd/dnsx@v1.1.7` |
| **`httpx`** | HTTP Probe | `v1.6.9` | `go install github.com/projectdiscovery/httpx/cmd/httpx@v1.6.9` |
| **`katana`** | Web Crawler | `v1.1.0` | `go install github.com/projectdiscovery/katana/cmd/katana@v1.1.0` |
| **`naabu`** | Port Scanner | `v2.3.1` | `go install github.com/projectdiscovery/naabu/v2/cmd/naabu@v2.3.1` |
| **`nuclei`** | Vuln Scanner | `v3.3.7` | `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@v3.3.7` |
| **`gau`** | URL Discovery | `v2.2.3` | `go install github.com/lc/gau/v2/cmd/gau@v2.2.3` |
| **`waybackurls`** | Archive URLs | `latest` | `go install github.com/tomnomnom/waybackurls@latest` |
| **`ffuf`** | Web Fuzzing | `v2.1.0` | `go install github.com/ffuf/ffuf/v2@v2.1.0` |
| **`dalfox`** | XSS Scanner | `v2.9.2` | `go install github.com/hahwul/dalfox/v2@v2.9.2` |
| **`sqlmap`** | SQL Injection | `apt / pipx` | `pipx install sqlmap` or `sudo apt install sqlmap` |
| **`amass`** | Attack Surface | `v4.2.0` | `go install github.com/owasp-amass/amass/v4/...@v4.2.0` |

---

## 🔒 Safety & Scope Controls

> [!IMPORTANT]
> BugHunter AI strictly adheres to the core rules of authorized bug bounty operations:
> 1. **Zero LLM Scope Validation**: AI is **never** permitted to evaluate or decide scope. All scope checks use deterministic Python matching.
> 2. **Exclusions Always Win**: If a target matches any exclusion rule, it is immediately denied regardless of wildcard allowances.
> 3. **Private IP & Cloud Metadata Defense**: RFC1918 and AWS/GCP/Azure instance metadata IPs (`169.254.169.254`) are strictly blocked.
> 4. **Human-in-the-Loop Active Verification**: High-impact or active payloads require explicit approval via `/approvals`.
> 5. **No Auto-Submission**: Reports are generated for human review and are never submitted to bug bounty platforms automatically.
> 6. **Append-Only Audit Log**: Every tool invocation, scope check, and approval decision is immutably recorded.

---

## 🤖 AI Engine Configuration

Configure your AI provider in `bughunter/backend/.env`:

```ini
# --- Option 1: OpenAI (Default) ---
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini

# --- Option 2: OpenRouter ---
AI_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=sk-or-v1-...
AI_MODEL=anthropic/claude-3.5-sonnet

# --- Option 3: Groq (Ultra-Fast) ---
AI_BASE_URL=https://api.groq.com/openai/v1
AI_API_KEY=gsk_...
AI_MODEL=llama-3.3-70b-versatile

# --- Option 4: Local Ollama (100% Offline & Free) ---
AI_BASE_URL=http://localhost:11434/v1
AI_API_KEY=ollama
AI_MODEL=qwen2.5-coder:latest
```

---

## 🚀 Quick Start & Setup Guides

### Mode 1: Windows Local Development (No Docker Needed)

No Docker Desktop or external databases required. BugHunter AI uses an async SQLite database engine out of the box:

```powershell
# 1. Clone the repository
git clone https://github.com/BOnzai58-lab/buzzzzgs.git
cd buzzzzgs\bughunter

# 2. Run the single-click dev launcher
.\run_dev.ps1
```

- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Default Admin Login**:
  - Email: `admin@bughunter.com`
  - Password: `AdminPassword123!`

---

### Mode 2: Kali Linux / Ubuntu (VirtualBox or Bare Metal)

When running inside a Kali Linux virtual machine:

```bash
# 1. Clone repository
git clone https://github.com/BOnzai58-lab/buzzzzgs.git
cd buzzzzgs/bughunter

# 2. Install all 12 tools and dependencies automatically (pinned versions)
chmod +x scripts/install_kali.sh
./scripts/install_kali.sh

# 3. Launch BugHunter AI services
chmod +x scripts/run_linux.sh
./scripts/run_linux.sh
```

- **Inside Kali VM**: Open browser to [http://localhost:3000](http://localhost:3000)
- **From Windows Host**: Open browser to `http://<KALI_VM_IP>:3000` (IP displayed in terminal banner).

---

### Mode 3: Docker Compose (Production)

For complete multi-user background worker execution with PostgreSQL 16 and Redis 7:

```bash
cd bughunter
cp .env.example .env
# Edit .env and configure strong POSTGRES_PASSWORD and SECRET_KEY
docker compose up -d
```

- All services are bound to `127.0.0.1` by default to prevent external exposure.
- Automated health checks monitor database readiness and Redis ping.

---

## 🧪 Running the Automated Test Suite

BugHunter AI includes an automated unit and integration test suite:

```bash
cd bughunter/backend

# Run the 46-test verification suite
python run_tests.py
# Or with virtual environment python:
.venv/bin/python run_tests.py        # Linux / Kali
.venv\Scripts\python.exe run_tests.py # Windows
```

The test runner covers:
1. **Scope Validator & SSRF**: Wildcard isolation, apex domain rules, IDN punycode, URL decoding, RFC1918 blocks, cloud metadata blocks, and redirect validation.
2. **Process Tracker**: Tool process registration, timeout handling, and OS-level termination.
3. **Verification Engine**: Curl reproduction command synthesis, redirect validation, and SHA-256 evidence hashing.
4. **Report Generator**: Markdown draft enforcement, CVSS accuracy, and missing evidence warnings.

---

## 🔄 How to Push Changes to GitHub

To save and push your updates to this repository:

```bash
# 1. Stage modified files
git add .

# 2. Commit your changes
git commit -m "Your descriptive commit message"

# 3. Push to GitHub
git push
```

---

## ⚖️ Ethical Disclosure & Legal Disclaimer

> [!WARNING]
> BugHunter AI is developed solely for authorized security assessments, penetration testing, and legitimate bug bounty research within explicitly defined scopes.  
> - Users must obtain explicit written authorization from target asset owners before initiating scans.
> - Unauthorized port scanning, reconnaissance, or testing against systems without permission is strictly prohibited and may violate local and international laws.
> - The developers assume no liability for misuse or damage caused by this software.
