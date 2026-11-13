# 🎯 BugHunter AI

> **Autonomous Bug Bounty Reconnaissance & Vulnerability Analysis Platform**  
> AI-powered, strictly scoped, batch hunting & queue management with Linux-native tool management.

---

## 🚀 Latest Updates: Master Development Specification Implementation

- **Exploitation Engine (§11)**: Real, attacker-mindset checks across SQL Injection (`sqlmap`), XSS (`dalfox`), SSRF (`nuclei`), IDOR/BOLA, Content Discovery (`ffuf`), Auth Bypass, and SSTI with safe, non-destructive flags.
- **Policy Enforcement Gateway (§4, §5.3)**: Central deterministic checkpoint validating scope, authorization, rate limits, and permanently prohibiting DoS/stress testing under all configurations.
- **Authorization Records Registry (§5.1)**: Dedicated `AuthorizationRecord` model and API endpoints tracking scope URLs, authorized assets, and expiration dates.
- **Universal Cross-Platform Stability**: Default zero-config SQLite database (`sqlite+aiosqlite:///./bughunter.db`), user-safe paths (`./data/evidence`), auto `.env` sync, and launchers for Linux (`scripts/run_linux.sh`) and Windows (`scripts/run_windows.ps1`).
- **Adaptive Assessment Planner (§9)**: Intelligent 10-step assessment cycle generating candidate checks based on discovered assets (CMS detection, API route inventory, client-side JS analysis, login/session inspection, file-handling, and parameter validation) with §9.3 status tracking (`planned`, `running`, `passed`, `potential`, `verified`, `skipped_by_policy`, `blocked_by_scope`, `unsupported`, `failed`).
- **Scan Limitation & Policy Manager (§6)**: Hierarchical server-side policy inheritance (`Global -> Program -> Target`) with conflict resolution favoring stricter rules. Supports scan profiles (`passive`, `low_impact`, `standard`, `extended`), rate limits (RPS, concurrency), and permanent blocks on prohibited attack operations (DoS, destructive payloads, brute force).
- **Evidence Secret Redaction Service (§12.1)**: Comprehensive sanitization of sensitive tokens (`Authorization: Bearer`, session cookies, passwords, JWTs, AWS keys, PEM private keys) in raw requests, raw responses, reproducible curl commands, and generated reports while preserving cryptographic proof and structural integrity.
- **Cross-Platform Compatibility Matrix (§19.8)**: 3-state platform abstraction in `tool_manager.py` distinguishing `application_supported` (True), `tool_supported` (OS-level support), and `installed` (binary found in PATH), reporting explicit `availability_status` (`AVAILABLE`, `NOT_INSTALLED`, `UNAVAILABLE_ON_PLATFORM`) across Linux, Windows, and macOS.
- **Resource-Level Access Control & RBAC (§17, §2.5)**: Enforces read-only permissions for `viewer` accounts (blocking scan initiation and data mutation with HTTP 403) and isolates resources between analysts.
- **Real Batch Execution (§2.1, P0)**: Removed all simulated stages, hardcoded status codes (`200 OK`), fake gateway titles, and mock technology arrays. Probes now execute real HTTP/HTTPS requests with TLS verification, extracting actual server headers and live crawler endpoints.
- **Privilege Escalation Defense (§2.2, P0)**: Removed `role` from the public registration schema (`UserCreate`). Server-side assignment defaults to `analyst`. Added admin-only role updates (`POST /auth/users/{id}/role`).
- **TLS Verification & Redirect Gating (§2.4, P0)**: Enforced `verify=True` by default on all verifier and worker requests. No unchecked redirects.
- **Strict Wildcard Matching (§1.1)**: `*.example.com` covers subdomains only. The root apex domain (`example.com`) requires an explicit rule.
- **SSRF & Cloud Metadata Defense (§1.1)**: Deterministically blocks RFC1918 private subnets and cloud metadata services (`169.254.169.254`).
- **HTTP 3xx Redirect Gating (§1.1)**: Prevents crawlers and probers from jumping out of scope via open redirects.
- **ProcessTracker Kill Stop (§1.2)**: Stopping scans terminates the OS process tree (`taskkill /F /T` on Windows, `SIGKILL` process groups on Linux).
- **Verification Engine (§1.3, §4.4)**: Safe, non-destructive verification with reproducible `curl` commands and SHA-256 evidence hashing.
- **Strict Verification Gating**: Transitioning findings to `verified` requires an impact note ($\ge$ 10 chars), confirmed scope, reproducible test, and real HTTP evidence.
- **WebSocket Ownership Check (§1.4)**: Ensures non-admin users only receive streaming logs for scans they started.
- **Evidence-Grounded Reports (§1.5, §4.6)**: All reports are generated as `DRAFT — HUMAN REVIEW REQUIRED` with cryptographic evidence hashes.
- **Automated Test Suite (§2.4, §6, §18)**: 125 automated unit and integration tests passing at 100% via `python run_tests.py`.

---

## 🐧 Running on Linux / Kali Linux (VirtualBox & Bare Metal)

BugHunter AI is fully optimized to run natively inside **Kali Linux, Debian 12+, and Ubuntu 22.04+** (such as inside a VirtualBox virtual machine).

### 1. Initial Dependency & Security Tools Setup
Inside your Kali Linux terminal, run the automated setup script:
```bash
chmod +x scripts/install_kali.sh
./scripts/install_kali.sh
```
This script automatically:
- Detects your Linux distribution and architecture.
- Installs necessary system packages: `golang-go`, `python3-venv`, `pipx`, `libpcap-dev`, `git`, `curl`.
- Configures Go environment variables and user-local binaries (`~/go/bin`, `~/.local/bin`).
- Installs pinned versions of all 12 security tools directly from official upstream sources.
- Downloads and updates official Nuclei vulnerability templates.
- Runs an operational self-test on each installed binary.

### 2. Launching BugHunter AI in Linux
Start both the FastAPI backend and React frontend with a single command:
```bash
chmod +x scripts/run_linux.sh
./scripts/run_linux.sh
```
- **Local Access (inside Kali VM browser)**:
  - Dashboard: [http://localhost:3000](http://localhost:3000)
  - API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Host Access (from Windows Host browser)**:
  - Access using your Kali VM IP (shown in terminal): `http://<KALI_IP>:3000`

---

## 🪟 Running on Windows (Local Development)

```powershell
cd bughunter
.\run_dev.ps1
```
- **Dashboard**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **Interactive API Docs (Swagger)**: `http://localhost:8000/docs`

#### Default Admin Credentials:
- **Email**: `admin@bughunter.com`
- **Password**: `AdminPassword123!`

---

## 🧪 Running Automated Tests

```bash
cd backend
python run_tests.py
```
Executes all 46 automated assertions covering Scope, ProcessTracker, VerificationEngine, and ReportGenerator.

---

## 📦 Batch Hunting Center (§10)

The **Batch Hunting Center** allows submitting and assessing multiple authorized targets in bulk:

1. **Target List Import**: Accepts `.txt`, `.csv`, `.json`, and manual multiline inputs with deduplication.
2. **Pre-Queue Authorization & Scope Validation**: 100% deterministic Python scope checking. Exclusions always take precedence.
3. **Persistent Background Execution**: Assessment jobs persist across computer restarts and browser closures.
4. **Queue & Emergency Controls**: Real-time Start, Pause, Resume, Cancel, and Global Emergency Stop.
5. **Scheduled Monitoring**: Automated recurring passive subdomain, DNS, and technology change discovery.
6. **Multi-Format Batch Reports**: Export assessment summaries in PDF, Markdown, JSON, and CSV.

---

## 🛠️ Linux Native Tool Manager

The upgraded **Tool Manager** detects and controls the following 12 core security tools (pinned versions):

| Tool | Category | Verified Version |
|---|---|---|
| `subfinder` | Subdomains | `v2.6.8` |
| `dnsx` | DNS Resolution | `v1.1.7` |
| `httpx` | HTTP Probing | `v1.6.9` |
| `katana` | Web Crawling | `v1.1.0` |
| `naabu` | Port Discovery | `v2.3.1` |
| `nuclei` | Vulnerabilities | `v3.3.7` |
| `gau` | URL Extraction | `v2.2.3` |
| `waybackurls` | Archive URLs | `latest` |
| `ffuf` | Web Fuzzing | `v2.1.0` |
| `dalfox` | XSS Analysis | `v2.9.2` |
| `sqlmap` | SQL Injection | `apt / pipx` |
| `amass` | Attack Surface | `v4.2.0` |
