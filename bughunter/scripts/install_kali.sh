#!/usr/bin/env bash
# ==============================================================================
# BugHunter AI — Native Security Tools & Environment Setup for Kali Linux / Debian
# Compatible with: Kali Linux (VirtualBox/bare-metal), Debian 12+, Ubuntu 22.04+
# ==============================================================================
set -e

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}          BugHunter AI — Kali Linux Security Tools Setup        ${NC}"
echo -e "${CYAN}================================================================${NC}"

# 1. Environment & Architecture Detection
ARCH=$(uname -m)
KERNEL=$(uname -r)
DISTRO="Linux"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$PRETTY_NAME
fi

echo -e "${BLUE}[*] OS Distribution : ${GREEN}$DISTRO${NC}"
echo -e "${BLUE}[*] Architecture    : ${GREEN}$ARCH${NC}"
echo -e "${BLUE}[*] Kernel          : ${GREEN}$KERNEL${NC}"
echo -e "${BLUE}[*] User            : ${GREEN}$(whoami)${NC}"

# Check for sudo if not root
SUDO=""
if [ "$EUID" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        echo -e "${RED}[!] Error: Please run as root or install sudo.${NC}"
        exit 1
    fi
fi

# 2. Update and Install Core System Dependencies
echo -e "\n${BLUE}[*] Installing system dependencies (git, curl, golang, python3, pipx, libpcap)...${NC}"
$SUDO apt-get update -y
$SUDO apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    golang-go \
    python3 \
    python3-pip \
    python3-venv \
    pipx \
    libpcap-dev \
    build-essential \
    ca-certificates

# 3. Setup User-Local Environment Directories
USER_HOME=${HOME:-/root}
GO_BIN="$USER_HOME/go/bin"
LOCAL_BIN="$USER_HOME/.local/bin"

mkdir -p "$GO_BIN" "$LOCAL_BIN"

export GOPATH="$USER_HOME/go"
export PATH="$GO_BIN:$LOCAL_BIN:/usr/local/go/bin:$PATH"

# Persist PATH in ~/.bashrc and ~/.zshrc if missing
for RC in "$USER_HOME/.bashrc" "$USER_HOME/.zshrc"; do
    if [ -f "$RC" ]; then
        if ! grep -q 'go/bin' "$RC"; then
            echo 'export GOPATH=$HOME/go' >> "$RC"
            echo 'export PATH=$PATH:$HOME/go/bin:$HOME/.local/bin:/usr/local/go/bin' >> "$RC"
            echo -e "${GREEN}[+] Added Go and local binaries to $RC${NC}"
        fi
    fi
done

# 4. Install 12 Core Security Tools
echo -e "\n${CYAN}[*] Installing 12 Core Security Tools...${NC}"

# Go Tools List — pinned versions with fallback for reproducibility (§2.1)
declare -A GO_TOOLS=(
    ["subfinder"]="github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.6.8"
    ["dnsx"]="github.com/projectdiscovery/dnsx/cmd/dnsx@v1.1.7"
    ["httpx"]="github.com/projectdiscovery/httpx/cmd/httpx@v1.6.9"
    ["katana"]="github.com/projectdiscovery/katana/cmd/katana@v1.1.0"
    ["naabu"]="github.com/projectdiscovery/naabu/v2/cmd/naabu@v2.3.1"
    ["nuclei"]="github.com/projectdiscovery/nuclei/v3/cmd/nuclei@v3.3.7"
    ["gau"]="github.com/lc/gau/v2/cmd/gau@v2.2.3"
    ["waybackurls"]="github.com/tomnomnom/waybackurls@latest"
    ["ffuf"]="github.com/ffuf/ffuf/v2@v2.1.0"
    ["dalfox"]="github.com/hahwul/dalfox/v2@v2.9.2"
    ["amass"]="github.com/owasp-amass/amass/v4/...@v4.2.0"
)

for tool in "${!GO_TOOLS[@]}"; do
    pkg="${GO_TOOLS[$tool]}"
    if command -v "$tool" >/dev/null 2>&1 || [ -x "$GO_BIN/$tool" ]; then
        echo -e "${GREEN}[✔] $tool is already installed.${NC}"
    else
        echo -e "${YELLOW}[→] Installing $tool from $pkg ...${NC}"
        go install -v "$pkg" || {
            echo -e "${RED}[✘] Failed to install $tool via go install${NC}"
        }
    fi
done

# 5. Install SQLMap
if command -v sqlmap >/dev/null 2>&1; then
    echo -e "${GREEN}[✔] sqlmap is already installed.${NC}"
else
    echo -e "${YELLOW}[→] Installing sqlmap...${NC}"
    $SUDO apt-get install -y sqlmap 2>/dev/null || pipx install sqlmap || pip3 install --user sqlmap
fi

# 6. Update Nuclei Templates
if command -v nuclei >/dev/null 2>&1 || [ -x "$GO_BIN/nuclei" ]; then
    echo -e "\n${BLUE}[*] Updating Nuclei vulnerability templates...${NC}"
    "$GO_BIN/nuclei" -update-templates || nuclei -update-templates || true
fi

# 7. Verification Summary
echo -e "\n${CYAN}================================================================${NC}"
echo -e "${CYAN}                    Tool Verification Report                    ${NC}"
echo -e "${CYAN}================================================================${NC}"

ALL_TOOLS=("subfinder" "dnsx" "httpx" "katana" "naabu" "nuclei" "gau" "waybackurls" "ffuf" "dalfox" "sqlmap" "amass")
INSTALLED=0

for t in "${ALL_TOOLS[@]}"; do
    BIN_PATH=$(command -v "$t" 2>/dev/null || true)
    if [ -z "$BIN_PATH" ] && [ -x "$GO_BIN/$t" ]; then
        BIN_PATH="$GO_BIN/$t"
    fi
    if [ -n "$BIN_PATH" ]; then
        INSTALLED=$((INSTALLED + 1))
        VER=$("$BIN_PATH" --version 2>&1 | head -n 1 || "$BIN_PATH" -version 2>&1 | head -n 1 || "$BIN_PATH" -h 2>&1 | head -n 1 || echo "OK")
        echo -e "${GREEN}[✔] $t${NC} -> $BIN_PATH (${CYAN}${VER:0:45}${NC})"
    else
        echo -e "${RED}[✘] $t${NC} -> Not found in PATH or $GO_BIN"
    fi
done

echo -e "\n${GREEN}[+] Verification complete: $INSTALLED / ${#ALL_TOOLS[@]} tools installed and ready.${NC}"
if [ "$INSTALLED" -lt "${#ALL_TOOLS[@]}" ]; then
    echo -e "${YELLOW}[!] Note: $(( ${#ALL_TOOLS[@]} - INSTALLED )) optional/core tools missing. BugHunter AI will operate with available tools or fallback modes.${NC}"
fi
echo -e "${YELLOW}[!] Make sure to reload your shell: source ~/.bashrc${NC}"
echo -e "${CYAN}================================================================${NC}"
