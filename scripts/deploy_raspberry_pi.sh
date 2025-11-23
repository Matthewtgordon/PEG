#!/bin/bash
# ==============================================================================
# APEG Deployment Script for Raspberry Pi
# ==============================================================================
# Handles installation, configuration, and systemd service setup for
# running APEG on Raspberry Pi or similar ARM-based Linux systems.
#
# Usage:
#   sudo ./deploy_raspberry_pi.sh
#
# Requirements:
#   - Ubuntu 22.04+ or Raspberry Pi OS (64-bit recommended)
#   - Python 3.11+
#   - Internet connection for package installation
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/apeg"
SERVICE_USER="apeg"
SERVICE_NAME="apeg"
PYTHON_VERSION="3.11"

echo "========================================="
echo " APEG System - Raspberry Pi Deployment"
echo "========================================="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Check if running on ARM/Raspberry Pi
ARCH=$(uname -m)
echo -e "${GREEN}Architecture:${NC} $ARCH"
if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" && "$ARCH" != "x86_64" ]]; then
    echo -e "${YELLOW}Warning: Untested architecture. Proceeding anyway...${NC}"
fi

# Check Python version
echo ""
echo "Checking Python version..."
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$PY_VER >= 3.11" | bc -l) -eq 1 ]]; then
        PYTHON_CMD="python3"
    else
        echo -e "${RED}Error: Python 3.11+ required, found $PY_VER${NC}"
        echo "Install with: sudo apt install python3.11 python3.11-venv"
        exit 1
    fi
else
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}Python:${NC} $($PYTHON_CMD --version)"

# Check for required source files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [[ ! -d "$PROJECT_DIR/src" ]]; then
    echo -e "${RED}Error: Source directory not found at $PROJECT_DIR/src${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Source directory:${NC} $PROJECT_DIR"
echo -e "${GREEN}Install directory:${NC} $INSTALL_DIR"

# Create service user if doesn't exist
echo ""
echo "Creating service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" -m "$SERVICE_USER"
    echo -e "${GREEN}Created user:${NC} $SERVICE_USER"
else
    echo -e "${YELLOW}User already exists:${NC} $SERVICE_USER"
fi

# Create installation directory
echo ""
echo "Setting up installation directory..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/logs"

# Copy application files
echo "Copying application files..."
cp -r "$PROJECT_DIR/src" "$INSTALL_DIR/"
cp -r "$PROJECT_DIR/config" "$INSTALL_DIR/" 2>/dev/null || mkdir -p "$INSTALL_DIR/config"
cp -r "$PROJECT_DIR/webui" "$INSTALL_DIR/"
cp "$PROJECT_DIR/requirements.txt" "$INSTALL_DIR/"

# Copy configuration files
for file in WorkflowGraph.json Agent_Prompts.json Rules.json Knowledge.json SessionConfig.json; do
    if [[ -f "$PROJECT_DIR/$file" ]]; then
        cp "$PROJECT_DIR/$file" "$INSTALL_DIR/"
    fi
done

# Set ownership
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
sudo -u "$SERVICE_USER" $PYTHON_CMD -m venv "$INSTALL_DIR/.venv"

# Upgrade pip and install dependencies
echo "Installing Python dependencies..."
sudo -u "$SERVICE_USER" "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip --quiet
sudo -u "$SERVICE_USER" "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --quiet

echo -e "${GREEN}Dependencies installed successfully${NC}"

# Create .env file if doesn't exist
ENV_FILE="$INSTALL_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo ""
    echo "Creating environment configuration..."
    cat > "$ENV_FILE" << 'EOF'
# APEG Environment Configuration
# Edit this file with your API credentials

# System Mode (true = test mode with dummy data)
APEG_TEST_MODE=true
APEG_DEBUG=false
APEG_HOST=0.0.0.0
APEG_PORT=8000

# Shopify API Credentials
# SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
# SHOPIFY_ACCESS_TOKEN=shpat_xxxxx

# Etsy API Credentials
# ETSY_API_KEY=your-api-key
# ETSY_API_SECRET=your-api-secret
# ETSY_SHOP_ID=your-shop-id

# OpenAI API Key (for LLM features)
# OPENAI_API_KEY=sk-xxxxx
EOF
    chown "$SERVICE_USER:$SERVICE_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo -e "${YELLOW}IMPORTANT: Edit $ENV_FILE with your API credentials${NC}"
fi

# Create systemd service file
echo ""
echo "Creating systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=APEG Agentic Orchestration System
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
Environment="PYTHONPATH=$INSTALL_DIR/src"
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn apeg_core.server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"

echo ""
echo "========================================="
echo -e "${GREEN}Deployment complete!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit configuration:"
echo "   sudo nano $INSTALL_DIR/.env"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status $SERVICE_NAME"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo ""

# Get IP address for access URL
IP_ADDR=$(hostname -I | awk '{print $1}')
echo "5. Access the web UI:"
echo "   http://${IP_ADDR}:8000"
echo "   http://${IP_ADDR}:8000/docs (API documentation)"
echo ""
echo "========================================="
echo ""
