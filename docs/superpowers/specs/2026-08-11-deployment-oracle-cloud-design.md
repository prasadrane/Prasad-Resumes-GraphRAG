# Spec: Docker-First Oracle Cloud Deployment

**Date:** 2026-08-11  
**Status:** Approved for implementation  
**Scope:** Fix 6 deployment issues + migrate from Vercel to Oracle Cloud Free Tier

## Problem Statement

The current deployment has 6 issues:
1. Python version drift — no pinning, Vercel defaults to latest, CI/Docker use 3.11
2. `vercel dev` broken locally — vercel_runtime needs Python 3.12+, local is 3.11
3. Dockerfile broken — wrong path (`run_litellm.py` vs `scripts/run_litellm.py`), missing `litellm` dep
4. Unpinned dependencies in requirements.txt — builds not reproducible
5. No favicon — browsers 404 on `/favicon.ico`
6. Static assets routed through Python function — slow, burns Vercel quota

Additionally, the Vercel serverless bundle has a ~50 MB limit, preventing real GraphRAG queries (requires `graphrag` + `lancedb` packages).

## Solution

Migrate to Oracle Cloud Free Tier (always-free ARM VM: 4 CPUs, 24GB RAM, 200GB storage) running Docker Compose. Fix all 6 issues as prerequisites.

## Architecture

Single Oracle Cloud ARM VM running Docker Compose with three services:

1. **web** — FastAPI app (`src/web/app.py`) on port 8000
   - Serves UI + API endpoints
   - Runs GraphRAG queries (local/global/DRIFT)
   - Resume generation pipeline
   
2. **litellm** — LiteLLM proxy on port 8002
   - Routes LLM requests to OpenRouter/Gemini
   - Internal only (not exposed externally)
   
3. **nginx** — Reverse proxy on ports 80/443
   - Routes to web/litellm
   - Auto-SSL via Let's Encrypt (certbot)
   - Serves static assets directly (HTML/CSS/JS)

## Components

### 1. Dockerfile (web service)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache layer)
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy app code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Run app
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: graphrag-web
    ports:
      - "8000:8000"
    volumes:
      - ./output:/app/output
      - ./input:/app/input
      - ./cache:/app/cache
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - FREELLMAPI_API_KEY=${FREELLMAPI_API_KEY}
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  litellm:
    build:
      context: .
      dockerfile: Dockerfile.litellm
    container_name: graphrag-litellm
    ports:
      - "8002:8002"
    volumes:
      - ./config/litellm-config.yaml:/app/config.yaml
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - FREELLMAPI_API_KEY=${FREELLMAPI_API_KEY}
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: graphrag-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./src/web/static:/usr/share/nginx/html:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - web
      - litellm
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3

  certbot:
    image: certbot/certbot
    container_name: graphrag-certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

### 3. nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream web {
        server web:8000;
    }

    upstream litellm {
        server litellm:8002;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # Let's Encrypt validation
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # Redirect HTTP to HTTPS
        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

        # Static assets (served directly by nginx)
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
        }

        # API routes (proxied to FastAPI)
        location /api/ {
            proxy_pass http://web;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # SSE streaming support
            proxy_buffering off;
            proxy_cache off;
        }

        # Favicon (static file)
        location /favicon.ico {
            root /usr/share/nginx/html;
        }
    }
}
```

### 4. Favicon

Add `favicon.ico` to `src/web/static/`. Can be a simple icon (e.g., resume document icon).

### 5. Python Version Pinning

Create `.python-version` file:
```
3.11
```

Update `vercel.json` to pin runtime:
```json
{
  "functions": {
    "api/index.py": {
      "runtime": "@vercel/python@4.3.0"
    }
  }
}
```

### 6. Pin Dependencies

Update `requirements.txt`:
```txt
fastapi==0.115.0
pydantic==2.9.2
reportlab==4.2.5
python-dotenv==1.0.1
pyyaml==6.0.2
uvicorn==0.32.0
graphrag==0.5.0
lancedb==0.15.0
```

### 7. Fix Dockerfile (LiteLLM proxy)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY scripts/run_litellm.py ./run_litellm.py
COPY config/litellm-config.yaml ./config.yaml

EXPOSE 8002

CMD ["python", "run_litellm.py"]
```

## CI/CD (GitHub Actions)

```yaml
name: Deploy to Oracle Cloud

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker images
        run: |
          docker-compose build

      - name: Push to GitHub Container Registry
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker tag graphrag-web ghcr.io/${{ github.repository }}/web:latest
          docker tag graphrag-litellm ghcr.io/${{ github.repository }}/litellm:latest
          docker push ghcr.io/${{ github.repository }}/web:latest
          docker push ghcr.io/${{ github.repository }}/litellm:latest

      - name: Deploy to Oracle VM
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.ORACLE_VM_HOST }}
          username: ${{ secrets.ORACLE_VM_USER }}
          key: ${{ secrets.ORACLE_VM_SSH_KEY }}
          script: |
            cd /opt/graphrag
            docker-compose pull
            docker-compose up -d
            docker system prune -f
```

## Data Flow

```
Browser → nginx (80/443)
  ├─ / → static HTML/CSS/JS (nginx serves directly)
  ├─ /favicon.ico → static file (nginx)
  └─ /api/* → web:8000 (FastAPI)
              ├─ /api/query → GraphRAG Python API
              ├─ /api/generate → resume generation pipeline
              └─ LLM calls → litellm:8002 → OpenRouter/Gemini
```

## Error Handling

- nginx returns 502 if web/litellm down
- FastAPI graceful degradation: if GraphRAG fails, fall back to static reader
- LiteLLM fallback chain: OpenRouter → Gemini (existing logic)
- Docker Compose restart policy: `unless-stopped`
- Health checks: nginx pings `/api/health`, restarts if 3 failures

## Deployment Verification

1. `docker-compose up -d` on Oracle VM
2. `curl https://<domain>/api/health` → 200
3. `curl https://<domain>/` → serves UI
4. Test resume generation via UI
5. Test GraphRAG query via UI

## LLM Strategy

- **Primary:** OpenRouter free models (`nvidia/nemotron-3-super-120b:free` for chat, `llama-nemotron-embed-vl-1b-v2` for embeddings)
- **Fallback:** Gemini 2.5 Flash free tier (15 req/min, 1M tokens/day)
- **Long-term:** Both have generous free tiers; Gemini provides stable fallback

## Migration Steps

1. Fix all 6 deployment issues locally
2. Create Oracle Cloud ARM VM instance
3. Install Docker + Docker Compose on VM
4. Set up domain DNS pointing to VM IP
5. Run certbot to obtain SSL certificate
6. Deploy via docker-compose
7. Verify all endpoints
8. Decommission Vercel deployment

## Success Criteria

- All 6 deployment issues resolved
- App accessible via HTTPS on custom domain
- Resume generation works end-to-end
- GraphRAG queries return answers
- CI/CD pipeline deploys on push to main
- Zero-downtime deployments (docker-compose pull + up -d)

## Out of Scope

- GraphRAG enhancements (separate spec)
- Multi-region deployment
- Auto-scaling
- Monitoring/alerting (future phase)
