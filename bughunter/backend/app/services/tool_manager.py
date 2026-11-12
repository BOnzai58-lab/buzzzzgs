"""Linux Native Security Tool Manager Service.
Detects Linux distribution, manages tool dependencies, performs version checks,
and safely runs user-local installs and updates for all 12 security tools.
"""
from __future__ import annotations

import asyncio
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from loguru import logger

# List of search paths for security tools
SEARCH_DIRS = [
    os.path.expanduser("~/go/bin"),
    os.path.expanduser("~/.local/bin"),
    "/usr/local/go/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
]

# Ensure user-local directories are in PATH
CURRENT_PATH = os.environ.get("PATH", "")
for d in [os.path.expanduser("~/go/bin"), os.path.expanduser("~/.local/bin"), "/usr/local/go/bin"]:
    if d not in CURRENT_PATH:
        os.environ["PATH"] = f"{d}:{CURRENT_PATH}"


TOOLS_CONFIG: dict[str, dict[str, Any]] = {
    "subfinder": {
        "version_cmd": ["subfinder", "-version"],
        "install_cmd": ["go", "install", "-v", "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"],
        "category": "subdomains",
        "description": "Fast passive subdomain enumeration tool",
        "doc_url": "https://github.com/projectdiscovery/subfinder",
    },
    "dnsx": {
        "version_cmd": ["dnsx", "-version"],
        "install_cmd": ["go", "install", "-v", "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"],
        "category": "dns",
        "description": "Fast and multi-purpose DNS toolkit",
        "doc_url": "https://github.com/projectdiscovery/dnsx",
    },
    "httpx": {
        "version_cmd": ["httpx", "-version"],
        "install_cmd": ["go", "install", "-v", "github.com/projectdiscovery/httpx/cmd/httpx@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/projectdiscovery/httpx/cmd/httpx@latest"],
        "category": "probe",
        "description": "Fast and multi-purpose HTTP probe toolkit",
        "doc_url": "https://github.com/projectdiscovery/httpx",
    },
    "katana": {
        "version_cmd": ["katana", "-version"],
        "install_cmd": ["go", "install", "-v", "github.com/projectdiscovery/katana/cmd/katana@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/projectdiscovery/katana/cmd/katana@latest"],
        "category": "crawler",
        "description": "Next-generation crawling and spidering framework",
        "doc_url": "https://github.com/projectdiscovery/katana",
    },
    "naabu": {
        "version_cmd": ["naabu", "-version"],
        "install_cmd": ["go", "install", "-v", "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"],
        "category": "ports",
        "description": "Fast port scanner written in Go with SYN/CONNECT scans",
        "doc_url": "https://github.com/projectdiscovery/naabu",
    },
    "nuclei": {
        "version_cmd": ["nuclei", "-version"],
        "install_cmd": ["go", "install", "-v", "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"],
        "update_cmd": ["nuclei", "-update-templates"],
        "category": "vulnerability",
        "description": "Fast and customizable vulnerability scanner based on simple YAML DSL",
        "doc_url": "https://github.com/projectdiscovery/nuclei",
    },
    "gau": {
        "version_cmd": ["gau", "--version"],
        "install_cmd": ["go", "install", "-v", "github.com/lc/gau/v2/cmd/gau@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/lc/gau/v2/cmd/gau@latest"],
        "category": "endpoints",
        "description": "Fetch known URLs from AlienVault, Wayback Machine, and Common Crawl",
        "doc_url": "https://github.com/lc/gau",
    },
    "waybackurls": {
        "version_cmd": ["waybackurls", "-h"],
        "install_cmd": ["go", "install", "-v", "github.com/tomnomnom/waybackurls@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/tomnomnom/waybackurls@latest"],
        "category": "endpoints",
        "description": "Fetch all the URLs that the Wayback Machine knows about for a domain",
        "doc_url": "https://github.com/tomnomnom/waybackurls",
    },
    "ffuf": {
        "version_cmd": ["ffuf", "-V"],
        "install_cmd": ["go", "install", "-v", "github.com/ffuf/ffuf/v2@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/ffuf/ffuf/v2@latest"],
        "category": "fuzzing",
        "description": "Fast web fuzzer written in Go",
        "doc_url": "https://github.com/ffuf/ffuf",
    },
    "dalfox": {
        "version_cmd": ["dalfox", "version"],
        "install_cmd": ["go", "install", "-v", "github.com/hahwul/dalfox/v2@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/hahwul/dalfox/v2@latest"],
        "category": "vulnerability",
        "description": "Finder of XSS and parameter analysis tool",
        "doc_url": "https://github.com/hahwul/dalfox",
    },
    "sqlmap": {
        "version_cmd": ["sqlmap", "--version"],
        "install_cmd": ["pip", "install", "--user", "sqlmap"],
        "update_cmd": ["pip", "install", "--user", "--upgrade", "sqlmap"],
        "category": "vulnerability",
        "description": "Automatic SQL injection and database takeover tool",
        "doc_url": "https://sqlmap.org",
    },
    "amass": {
        "version_cmd": ["amass", "-version"],
        "install_cmd": ["go", "install", "-v", "github.com/owasp-amass/amass/v4/...@latest"],
        "update_cmd": ["go", "install", "-v", "github.com/owasp-amass/amass/v4/...@latest"],
        "category": "subdomains",
        "description": "In-depth attack surface mapping and asset discovery",
        "doc_url": "https://github.com/owasp-amass/amass",
    },
}


class LinuxToolManager:
    """Manages system environment detection and installation lifecycle for security tools."""

    _active_tasks: dict[str, asyncio.Task] = {}
    _tool_logs: dict[str, list[dict]] = {}
    _tool_status_cache: dict[str, dict] = {}

    @classmethod
    def get_system_info(cls) -> dict:
        """Inspects OS distribution, architecture, Go, Python, and PATH configuration."""
        distro = "Unknown Linux"
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release") as f:
                    content = f.read()
                    name_match = re.search(r'PRETTY_NAME="([^"]+)"', content) or re.search(r"NAME=([^\n]+)", content)
                    if name_match:
                        distro = name_match.group(1).strip('"')
            except Exception:
                pass
        elif platform.system() == "Windows":
            distro = f"Windows {platform.release()}"
        else:
            distro = f"{platform.system()} {platform.release()}"

        go_path = shutil.which("go")
        go_version = None
        if go_path:
            try:
                out = subprocess.run([go_path, "version"], capture_output=True, text=True, timeout=3)
                go_version = out.stdout.strip()
            except Exception:
                pass

        python_path = shutil.which("python3") or shutil.which("python")
        python_version = None
        if python_path:
            try:
                out = subprocess.run([python_path, "--version"], capture_output=True, text=True, timeout=3)
                python_version = (out.stdout or out.stderr).strip()
            except Exception:
                pass

        pipx_path = shutil.which("pipx")
        git_path = shutil.which("git")

        return {
            "os_name": platform.system(),
            "distribution": distro,
            "architecture": platform.machine(),
            "is_linux": platform.system() == "Linux",
            "is_kali": "kali" in distro.lower(),
            "go_installed": go_path is not None,
            "go_version": go_version,
            "go_path": go_path,
            "python_version": python_version,
            "python_path": python_path,
            "pipx_installed": pipx_path is not None,
            "git_installed": git_path is not None,
            "user_home": str(Path.home()),
            "path_directories": [p for p in os.environ.get("PATH", "").split(os.pathsep) if p],
        }

    @classmethod
    def locate_tool_binary(cls, tool_name: str) -> str | None:
        """Finds executable path checking standard PATH and user-local go/bin directories."""
        # 1. Standard which
        p = shutil.which(tool_name)
        if p:
            return p

        # 2. Check candidate directories directly
        candidates = [
            os.path.expanduser(f"~/go/bin/{tool_name}"),
            os.path.expanduser(f"~/.local/bin/{tool_name}"),
            f"/usr/local/go/bin/{tool_name}",
            f"/usr/local/bin/{tool_name}",
            f"/usr/bin/{tool_name}",
        ]
        if platform.system() == "Windows":
            candidates.extend([
                os.path.expanduser(f"~/go/bin/{tool_name}.exe"),
                os.path.expanduser(f"~/.local/bin/{tool_name}.exe"),
            ])

        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c
            elif platform.system() == "Windows" and os.path.isfile(c):
                return c

        return None

    @classmethod
    def verify_tool(cls, tool_name: str) -> dict:
        """Verifies binary existence and queries version string safely."""
        config = TOOLS_CONFIG.get(tool_name)
        if not config:
            return {"name": tool_name, "status": "Not Installed", "installed": False, "version": None}

        # Check if currently installing
        if tool_name in cls._active_tasks and not cls._active_tasks[tool_name].done():
            return {
                "name": tool_name,
                "status": "Installing",
                "installed": False,
                "version": None,
                "path": None,
                "category": config["category"],
                "description": config["description"],
            }

        binary_path = cls.locate_tool_binary(tool_name)
        if not binary_path:
            return {
                "name": tool_name,
                "status": "Not Installed",
                "installed": False,
                "version": None,
                "path": None,
                "category": config["category"],
                "description": config["description"],
            }

        # Run version command
        version_str = None
        cmd = [binary_path] + config["version_cmd"][1:]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            raw = (res.stdout or res.stderr or "").strip()
            # Extract first meaningful version line
            for line in raw.splitlines():
                line = line.strip()
                if line and not line.startswith("Usage:") and not line.startswith("Flags:"):
                    version_str = line[:80]
                    break
            if not version_str and raw:
                version_str = raw[:80]
        except Exception as e:
            logger.debug(f"Version check failed for {tool_name}: {e}")

        status = "Installed"
        return {
            "name": tool_name,
            "status": status,
            "installed": True,
            "version": version_str or "Installed",
            "path": binary_path,
            "category": config["category"],
            "description": config["description"],
            "doc_url": config["doc_url"],
        }

    @classmethod
    def list_all_tools(cls) -> list[dict]:
        results = []
        for name in TOOLS_CONFIG.keys():
            info = cls.verify_tool(name)
            results.append(info)
        return results

    @classmethod
    def get_logs(cls, tool_name: str) -> list[dict]:
        return cls._tool_logs.get(tool_name, [])

    @classmethod
    def append_log(cls, tool_name: str, message: str, level: str = "INFO"):
        if tool_name not in cls._tool_logs:
            cls._tool_logs[tool_name] = []
        cls._tool_logs[tool_name].append({
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        })
        # Keep last 500 lines
        if len(cls._tool_logs[tool_name]) > 500:
            cls._tool_logs[tool_name] = cls._tool_logs[tool_name][-500:]

    @classmethod
    async def install_tool(cls, tool_name: str, update_mode: bool = False) -> dict:
        """Installs or updates a tool asynchronously using official upstream methods."""
        config = TOOLS_CONFIG.get(tool_name)
        if not config:
            raise ValueError(f"Unknown tool: {tool_name}")

        if tool_name in cls._active_tasks and not cls._active_tasks[tool_name].done():
            return {"status": "already_running", "tool": tool_name}

        cls._tool_logs[tool_name] = []
        action = "update" if update_mode else "install"
        cls.append_log(tool_name, f"Starting {action} for {tool_name}...")

        # Pre-dependency check for Go tools
        cmd = config["update_cmd"] if update_mode else config["install_cmd"]
        if cmd[0] == "go" and not shutil.which("go"):
            cls.append_log(tool_name, "Dependency missing: Go (golang) is not installed on system.", level="ERROR")
            return {"status": "error", "message": "Go is not installed. Please install golang-go."}

        task = asyncio.create_task(cls._execute_install_job(tool_name, cmd, action))
        cls._active_tasks[tool_name] = task
        return {"status": "started", "tool": tool_name, "action": action}

    @classmethod
    async def _execute_install_job(cls, tool_name: str, cmd: list[str], action: str):
        cls.append_log(tool_name, f"Executing: {' '.join(cmd)}")
        env = os.environ.copy()
        
        # Ensure Go user environment is active
        go_path = os.path.expanduser("~/go")
        env["GOPATH"] = go_path
        env["PATH"] = f"{go_path}/bin:/usr/local/go/bin:{env.get('PATH', '')}"

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            async def stream_output(stream, level):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode(errors="replace").rstrip()
                    if decoded:
                        cls.append_log(tool_name, decoded, level=level)

            await asyncio.gather(
                stream_output(process.stdout, "INFO"),
                stream_output(process.stderr, "WARN"),
            )
            returncode = await process.wait()

            if returncode == 0:
                # Post-install verification
                verification = cls.verify_tool(tool_name)
                if verification["installed"]:
                    cls.append_log(tool_name, f"SUCCESS: {tool_name} installed successfully! ({verification.get('version', '')})", level="SUCCESS")
                else:
                    cls.append_log(tool_name, f"WARNING: Command finished but binary not found in PATH or ~/go/bin.", level="WARN")
            else:
                cls.append_log(tool_name, f"FAILED: Process exited with code {returncode}", level="ERROR")

        except Exception as exc:
            cls.append_log(tool_name, f"ERROR executing installer: {exc}", level="ERROR")
            logger.error(f"Installation failed for {tool_name}: {exc}")

    @classmethod
    async def install_all(cls) -> dict:
        """Triggers installation for all missing tools."""
        started = []
        for name, config in TOOLS_CONFIG.items():
            status = cls.verify_tool(name)
            if not status["installed"]:
                await cls.install_tool(name, update_mode=False)
                started.append(name)
        return {"status": "started", "tools": started}

    @classmethod
    async def update_all(cls) -> dict:
        """Triggers update for all installed tools."""
        started = []
        for name in TOOLS_CONFIG.keys():
            await cls.install_tool(name, update_mode=True)
            started.append(name)
        return {"status": "started", "tools": started}

