# 🎯 BugHunter AI

> **Autonomous Bug Bounty Reconnaissance & Vulnerability Analysis Platform**  
> AI-powered, strictly scoped, batch hunting & queue management with Linux-native tool management.

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
- Installs and verifies all 12 security tools directly from official upstream sources.
- Downloads and updates official Nuclei vulnerability templates.

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

## 📦 Batch Hunting Center (§10)

The **Batch Hunting Center** allows submitting and assessing multiple authorized targets in bulk:

1. **Target List Import**:
   - Accepts `.txt`, `.csv`, `.json`, and manual multiline inputs.
   - Automatic normalization of URLs, FQDNs, CIDR ranges, and IP addresses.
   - Deduplication prevents repeating work across active assessments.
2. **Pre-Queue Authorization & Scope Validation**:
   - 100% deterministic Python scope checking.
   - Target eligibility statuses: `VALIDATED`, `OUT_OF_SCOPE`, `EXCLUDED`, `NEEDS_PROGRAM_MATCH`, `POLICY_EXPIRED`, `READY_TO_QUEUE`.
   - Exclusions-first precedence ensures forbidden domains are never queued.
3. **Persistent Background Execution**:
   - Assessment jobs persist in database across computer restarts and browser closures.
   - Supports **Local Mode** and **Server Mode** for always-on VPS deployments.
4. **Queue & Emergency Controls**:
   - Real-time **Start**, **Pause**, **Resume**, and **Cancel** controls.
   - **Global Emergency Stop**: Immediately halts job dispatch, terminates active tool processes, closes outbound egress, and immutably logs the action in `AuditLog`.
5. **Scheduled Monitoring**:
   - Automated recurring passive subdomain, DNS, and technology change discovery with customizable quiet hours and execution budgets.
6. **Multi-Format Batch Reports**:
   - Export assessment summaries in **PDF**, **Markdown**, **JSON**, and **CSV**.

---

## 🛠️ Linux Native Tool Manager

The upgraded **Tool Manager** detects and controls the following 12 core security tools:

| # | Tool | Category | Installation Method |
|---|---|---|---|
| 1 | `subfinder` | Subdomains | `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest` |
| 2 | `dnsx` | DNS Resolution | `go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest` |
| 3 | `httpx` | HTTP Probing | `go install github.com/projectdiscovery/httpx/cmd/httpx@latest` |
| 4 | `katana` | Web Crawling | `go install github.com/projectdiscovery/katana/cmd/katana@latest` |
| 5 | `naabu` | Port Discovery | `go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest` |
| 6 | `nuclei` | Vulnerabilities | `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest` |
| 7 | `gau` | URL Extraction | `go install github.com/lc/gau/v2/cmd/gau@latest` |
| 8 | `waybackurls` | Archive URLs | `go install github.com/tomnomnom/waybackurls@latest` |
| 9 | `ffuf` | Web Fuzzing | `go install github.com/ffuf/ffuf/v2@latest` |
| 10 | `dalfox` | XSS Analysis | `go install github.com/hahwul/dalfox/v2@latest` |
| 11 | `sqlmap` | SQL Injection | `pipx install sqlmap` or `apt install sqlmap` |
| 12 | `amass` | Attack Surface | `go install github.com/owasp-amass/amass/v4/...@latest` |

### Tool Manager Features:
- **Environment Detection**: Inspects Linux distro, architecture, Go compiler version, Python path, and search directories.
- **Bulk & Individual Actions**: `Install All`, `Update All`, `Install`, `Update`, `Refresh Status`.
- **Live Execution Logs**: Real-time streaming modal showing installer stdout/stderr with timestamped output.
- **Safe Execution**: All installation tasks execute via user-local paths with an allowlist; no arbitrary frontend shell injection is permitted.
