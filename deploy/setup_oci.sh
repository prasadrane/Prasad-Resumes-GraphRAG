#!/bin/bash
# ==============================================================================
# Setup Script for Oracle Cloud Always Free VM (Ubuntu 22.04 / 24.04 LTS)
# Installs Docker, Docker Compose, Git, and configures firewall rules.
# ==============================================================================

set -e

echo "=========================================================="
echo "🚀 Initializing Oracle Cloud VM Setup for GraphRAG App..."
echo "=========================================================="

# 1. Update system packages
echo "📦 Updating APT packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release git ufw

# 2. Install Docker & Docker Compose Plugin
echo "🐳 Installing Docker Engine & Docker Compose..."
if ! command -v docker &> /dev/null; then
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker "$USER"
    echo "✅ Docker installed successfully."
else
    echo "✅ Docker is already installed."
fi

# 3. Configure Firewall & Oracle iptables Ingress
echo "🛡️ Configuring network ports (80, 443, 22)..."
# Oracle Ubuntu images have strict default iptables rules
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8002 -j ACCEPT

# Save iptables rules so they persist across VM reboots
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save

# 4. Clone Repository if not present
DEPLOY_DIR="${HOME}/Prasad-Resumes-GraphRAG"
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "📥 Cloning Prasad-Resumes-GraphRAG repository..."
    git clone https://github.com/prasadrane/Prasad-Resumes-GraphRAG.git "$DEPLOY_DIR"
fi

cd "$DEPLOY_DIR"

# 5. Create .env template if missing
if [ ! -f .env ]; then
    echo "📝 Creating .env template file..."
    cat <<EOF > .env
# Primary LLM Provider
ALIBABA_API_KEY=
OPENROUTER_API_KEY=
GEMINI_API_KEY=
GRAPHRAG_API_KEY=
FREELLMAPI_API_KEY=
EOF
    echo "⚠️ Please edit ${DEPLOY_DIR}/.env with your API keys!"
fi

echo "=========================================================="
echo "🎉 Setup complete! You can now log out and back in, or run:"
echo "   cd ~/Prasad-Resumes-GraphRAG"
echo "   docker compose up -d --build"
echo "=========================================================="
