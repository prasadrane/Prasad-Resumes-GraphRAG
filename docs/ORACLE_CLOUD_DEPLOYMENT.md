# Oracle Cloud (OCI Always Free) Automated Deployment Guide

This guide walks you through setting up a **100% free, high-performance Oracle Cloud VM** (4 OCPU ARM, 24 GB RAM) and configuring **automated, zero-touch CI/CD with GitHub Actions**.

---

## 🏗️ Architecture Overview

```mermaid
graph LR
    Dev[Local Code Commit / Push] --> Git[GitHub Repository: master]
    Git --> GHA[GitHub Actions CI/CD]
    GHA -->|1. Run 367 Tests| Test[Unit Tests Pass]
    Test -->|2. SSH Connection| OCI[Oracle Cloud Always Free VM]
    OCI -->|3. Git Pull & Docker Compose| App[Docker: Web + LiteLLM + Nginx]
```

- **0 Cold Starts:** The FastAPI server and LiteLLM proxy run 24/7 in memory.
- **Automated Deployments:** Every `git push` to `master` triggers GitHub Actions to run the full test suite and remotely deploy to your Oracle VM via SSH.
- **Zero Ongoing Maintenance:** Docker handles restarts, log rotation, and container health checks.

---

## 📋 Step 1: Create Oracle Cloud Always Free VM

1. Log in to your [Oracle Cloud Console](https://cloud.oracle.com/).
2. Navigate to **Compute** $\rightarrow$ **Instances** $\rightarrow$ **Create Instance**.
3. Configure the VM:
   - **Name:** `prasad-graphrag-vm`
   - **Image:** `Canonical Ubuntu 22.04 LTS` or `24.04 LTS`
   - **Shape:** `Ampere A1 (ARM)` — Choose **4 OCPU** and **24 GB RAM** (*Always Free Eligible*).
   - **Networking:** Select default VCN and assign a **Public IPv4 Address**.
   - **SSH Keys:** Generate or upload your SSH Public Key (save the Private Key locally as `oci_private_key.pem`).
4. Click **Create** and wait ~60 seconds for the VM state to change to `Running`. Note your **Public IP Address**.

---

## 🛡️ Step 2: Configure Oracle Cloud VCN Firewall (Ingress Rules)

Oracle Cloud blocks incoming web traffic at the VCN subnet level by default.

1. In the Oracle Console, go to **Networking** $\rightarrow$ **Virtual Cloud Networks**.
2. Click your VCN $\rightarrow$ **Security Lists** $\rightarrow$ **Default Security List for...**.
3. Under **Ingress Rules**, click **Add Ingress Rules**:
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** `TCP`
   - **Destination Port Range:** `80,443`
   - **Description:** `Allow HTTP and HTTPS traffic`
4. Click **Add Ingress Rules**.

---

## ⚡ Step 3: Run One-Time VM Bootstrap Script

SSH into your new VM from your local machine:

```powershell
ssh -i "path/to/oci_private_key.pem" ubuntu@<YOUR_VM_PUBLIC_IP>
```

Run the automated bootstrap setup script:

```bash
curl -fsSL https://raw.githubusercontent.com/prasadrane/Prasad-Resumes-GraphRAG/master/deploy/setup_oci.sh | bash
```

This installs:
- Docker Engine & Docker Compose Plugin
- Git, UFW, and persistent iptables rules for ports 80 and 443
- Clones the repository to `~/Prasad-Resumes-GraphRAG`

Add your API keys to the VM's `.env` file:
```bash
nano ~/Prasad-Resumes-GraphRAG/.env
```
*(Paste your `ALIBABA_API_KEY`, `OPENROUTER_API_KEY`, and `GEMINI_API_KEY`, then press `Ctrl+O`, `Enter`, `Ctrl+X`).*

---

## 🤖 Step 4: Configure GitHub Actions for Automated Deployment

To enable zero-touch automated deployments on every `git push`:

1. Go to your GitHub repository $\rightarrow$ **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
2. Click **New repository secret** and add the following 3 secrets:

| Secret Name | Value | Description |
| :--- | :--- | :--- |
| `OCI_HOST` | `<YOUR_VM_PUBLIC_IP>` | The public IP of your Oracle VM |
| `OCI_USERNAME` | `ubuntu` | Default SSH user for Ubuntu images |
| `OCI_SSH_KEY` | *(Paste entire contents of `oci_private_key.pem`)* | OpenSSH Private Key (starts with `-----BEGIN OPENSSH PRIVATE KEY-----`) |

---

## 🚀 How Automated Deployment Works

From now on, whenever you push code or merge a PR:

```powershell
git add .
git commit -m "feat: enhance feature"
git push origin master
```

1. GitHub Actions initiates [`.github/workflows/deploy-oci.yml`](file:///c:/Users/mamat/Github/Prasad-Resumes-GraphRAG/.github/workflows/deploy-oci.yml).
2. It executes all 367 unit tests.
3. Upon passing, it connects securely over SSH to your Oracle VM.
4. It pulls the latest code and runs `docker compose up -d --build`.
5. Your live app at `http://<YOUR_VM_PUBLIC_IP>` is updated in **~45 seconds** with **zero downtime**.
