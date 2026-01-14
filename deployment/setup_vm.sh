#!/bin/bash

# Exit on any error
set -e

APP_DIR="/opt/sharepoint_rag"
SOURCE_DIR=$(pwd)

echo "Starting deployment setup..."

# 1. Install System Dependencies (Ubuntu/Debian)
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip build-essential

# 2. Setup Application Directory
echo "Setting up application directory at $APP_DIR..."
sudo mkdir -p "$APP_DIR"

# Copy files from current location to /opt/sharepoint_rag
# Exclude venv and __pycache__ to avoid architecture mismatches
echo "Copying application files..."
sudo rsync -av --exclude='venv' --exclude='__pycache__' --exclude='.git' ./ "$APP_DIR/"

# 3. Setup Virtual Environment
echo "Creating Python virtual environment..."
cd "$APP_DIR"
if [ ! -d "venv" ]; then
    sudo python3 -m venv venv
fi

# 4. Install Python Dependencies
echo "Installing Python requirements..."
sudo "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo "$APP_DIR/venv/bin/pip" install -r requirements.txt

# 5. Configure Systemd Service
echo "Configuring Systemd service..."
# Check if .env exists, if not warn user
if [ ! -f "$APP_DIR/.env" ]; then
    echo "WARNING: .env file not found in $APP_DIR. Application may fail to start."
    echo "Please create $APP_DIR/.env with necessary secrets."
fi

sudo cp "$APP_DIR/deployment/sharepoint_rag.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sharepoint_rag
sudo systemctl restart sharepoint_rag

echo "================================================"
echo "Deployment Complete!"
echo "Service status:"
sudo systemctl status sharepoint_rag --no-pager
echo "================================================"
echo "API should be accessible at http://<YOUR_VM_IP>:8000"
