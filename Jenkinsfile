pipeline {
  agent any

  environment {
    IMAGE_NAME = "suneeth4518/spe-calculator"
    DOCKERHUB  = credentials('dockerhub-creds')   // $DOCKERHUB_USR / $DOCKERHUB_PSW
    PY3        = "/opt/homebrew/bin/python3"      // system python to create venvs
    // Absolute paths for CLIs on your Mac:
    ANS_GALAXY = "/opt/homebrew/bin/ansible-galaxy"
    NGROK      = "/opt/homebrew/bin/ngrok"
    GH_API     = "https://api.github.com"
    GH_OWNER   = "Suneeth4518"
    GH_REPO    = "spe-calculator-devops"
    // Optional: if you prefer your static ngrok domain, set it here.
    // Leave empty to auto-detect via ngrok API (localhost:4040)
    STATIC_NGROK_URL = "https://gullibly-clinometric-demi.ngrok-free.dev"
  }

  triggers { githubPush() }

  options {
    // Keeps logs readable and stops at first failing command in sh blocks
    ansiColor('xterm')
    timestamps()
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Test') {
      steps {
        sh '''
          set -e
          ${PY3} -m venv .venv
          . .venv/bin/activate
          python -m pip install --upgrade pip
          pip install -r requirements.txt

          mkdir -p reports
          pytest -q --junitxml=reports/pytest.xml
        '''
      }
      post {
        always { junit 'reports/pytest.xml' }
      }
    }

    stage('Build Docker Image') {
      steps {
        sh '''
          set -e
          DOCKER_BIN=$(which docker)
          echo "Using docker at: $DOCKER_BIN"
          $DOCKER_BIN build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:latest .
        '''
      }
    }

    stage('Push to Docker Hub') {
      steps {
        sh '''
          set -e
          DOCKER_BIN=$(which docker)
          echo $DOCKERHUB_PSW | $DOCKER_BIN login -u $DOCKERHUB_USR --password-stdin
          $DOCKER_BIN push ${IMAGE_NAME}:${BUILD_NUMBER}
          $DOCKER_BIN push ${IMAGE_NAME}:latest
        '''
      }
    }

    stage('Deploy via Ansible') {
      steps {
        sh '''
          set -euo pipefail

          # Create an isolated control venv for Ansible + python libs (avoids PEP 668 issues)
          if [ ! -d ".ansctl" ]; then
            ${PY3} -m venv .ansctl
          fi
          . .ansctl/bin/activate
          python -m pip install --upgrade pip
          pip install "ansible>=9" packaging requests docker PyYAML jinja2

          # Ensure the required collection is present
          .ansctl/bin/ansible-galaxy collection list | grep -q community.docker \
            || .ansctl/bin/ansible-galaxy collection install community.docker

          # Run the playbook using the venv's python as interpreter
          # NOTE: deploy/hosts.ini should NOT hardcode ansible_python_interpreter anymore.
          .ansctl/bin/ansible-playbook \
            -i deploy/hosts.ini \
            deploy/deploy.yml \
            --extra-vars "ansible_python_interpreter=${WORKSPACE}/.ansctl/bin/python image=${IMAGE_NAME}:latest container_name=spe-calc app_port=5000"
        '''
      }
    }

    stage('Upsert GitHub Webhook') {
      environment {
        // Your GitHub PAT stored in Jenkins credentials as a "Secret text" id=github-token
        // Must have: admin:repo_hook (and repo if the repo is private)
      }
      steps {
        withCredentials([string(credentialsId: 'github-token', variable: 'GH_TOKEN')]) {
          sh '''
            set -euo pipefail

            # 1) Ensure ngrok is running and get public URL
            if ! pgrep -f "${NGROK} http 5000" >/dev/null 2>&1; then
              nohup ${NGROK} http 5000 --log=stdout >/dev/null 2>&1 &
            fi

            # Wait up to ~10s for ngrok API to respond
            for i in $(seq 1 20); do
              if curl -sS http://127.0.0.1:4040/api/tunnels >/dev/null; then
                break
              fi
              sleep 0.5
            done

            APP_URL=""
            # Prefer STATIC_NGROK_URL if provided (free static subdomain)
            if [ -n "${STATIC_NGROK_URL}" ]; then
              APP_URL="${STATIC_NGROK_URL}"
            else
              APP_URL=$(${PY3} - <<'PY'
import json, urllib.request
try:
    data = json.load(urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels"))
    tunnels = [t for t in data.get("tunnels", []) if t.get("public_url","").startswith("https://")]
    if tunnels:
        print(tunnels[0]["public_url"])
except Exception:
    pass
PY
)
            fi

            if [ -z "${APP_URL}" ]; then
              echo "ERROR: Could not determine public URL for the app."
              exit 1
            fi

            echo "App is publicly reachable at: ${APP_URL}"
            HOOK_TARGET="${APP_URL%/}/github-webhook/"

            AUTH_H="Authorization: Bearer ${GH_TOKEN}"
            API="${GH_API}/repos/${GH_OWNER}/${GH_REPO}/hooks"

            # 2) List existing hooks (NO -f so we can inspect error body)
            HTTP=$(curl -sS -w "%{http_code}" -H "$AUTH_H" -H "Accept: application/vnd.github+json" \
                   -o hooks.json "$API")

            if [ "$HTTP" -lt 200 ] || [ "$HTTP" -ge 300 ]; then
              echo "GitHub API error while listing hooks (HTTP $HTTP):"
              cat hooks.json || true
              exit 1
            fi

            # 3) Find an existing Jenkins webhook (by URL suffix)
            HOOK_ID=$(${PY3} - <<'PY'
import json, sys
try:
    hooks = json.load(open("hooks.json","r"))
except Exception:
    hooks = []
for h in hooks:
    url = (h.get("config") or {}).get("url","")
    if url.endswith("/github-webhook/"):
        print(h.get("id") or "")
        break
PY
)

            # 4) Create or update the webhook
            if [ -z "$HOOK_ID" ]; then
              echo "Creating webhook → $HOOK_TARGET"
              HTTP=$(curl -sS -w "%{http_code}" -H "$AUTH_H" -H "Accept: application/vnd.github+json" \
                     -H "Content-Type: application/json" \
                     -o resp.json -X POST "$API" \
                     -d '{"name":"web","active":true,"events":["push"],"config":{"url":"'"$HOOK_TARGET"'","content_type":"json"}}')
            else
              echo "Updating webhook ${HOOK_ID} → $HOOK_TARGET"
              HTTP=$(curl -sS -w "%{http_code}" -H "$AUTH_H" -H "Accept: application/vnd.github+json" \
                     -H "Content-Type: application/json" \
                     -o resp.json -X PATCH "${API}/${HOOK_ID}" \
                     -d '{"config":{"url":"'"$HOOK_TARGET"'","content_type":"json"}}')
            fi

            if [ "$HTTP" -lt 200 ] || [ "$HTTP" -ge 300 ]; then
              echo "GitHub API error while creating/updating hook (HTTP $HTTP):"
              cat resp.json || true
              exit 1
            fi

            echo "Webhook upsert OK."
          '''
        }
      }
    }
  }
}

