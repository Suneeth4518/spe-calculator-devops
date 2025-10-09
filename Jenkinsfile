pipeline {
  agent any

  environment {
    IMAGE_NAME   = "suneeth4518/spe-calculator"
    DOCKERHUB    = credentials('dockerhub-creds')
    PY3          = "/opt/homebrew/bin/python3"
    DOCKER       = "/usr/local/bin/docker"
    NGROK        = "/opt/homebrew/bin/ngrok"
    GITHUB_TOKEN = credentials('github-token')
    GITHUB_OWNER = "Suneeth4518"
    GITHUB_REPO  = "spe-calculator-devops"
  }

  triggers { githubPush() }

  stages {

    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Expose Jenkins & Ensure GitHub Webhook') {
      steps {
        withCredentials([string(credentialsId: 'ngrok-authtoken', variable: 'NGROK_AUTHTOKEN')]) {
          sh '''
            set -euo pipefail

            # 0) Ensure ngrok is configured (optional – only if you provided ngrok-authtoken)
            if [ -n "${NGROK_AUTHTOKEN:-}" ]; then
              ${NGROK} config add-authtoken "${NGROK_AUTHTOKEN}" >/dev/null 2>&1 || true
            fi

            # 1) Start ngrok to expose Jenkins (PORT 8080), not the app.
            if ! pgrep -f "${NGROK} http 8080" >/dev/null 2>&1; then
              nohup ${NGROK} http 8080 --log=stdout >/dev/null 2>&1 &
            fi

            # 2) Wait for tunnel to be ready and grab the https public URL
            for i in $(seq 1 40); do
              if curl -fsS http://127.0.0.1:4040/api/tunnels >/dev/null 2>&1; then
                break
              fi
              sleep 0.5
            done
            APP_URL="$(${PY3} - <<'PY'
import json,sys,urllib.request
try:
  data=json.load(urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels'))
  for t in data.get('tunnels',[]):
    if t.get('proto')=='https':
      print(t.get('public_url'))
      sys.exit(0)
except Exception as e:
  pass
sys.exit(1)
PY
)"
            if [ -z "${APP_URL}" ]; then
              echo "Failed to get ngrok public URL" >&2
              exit 1
            fi
            echo "Jenkins is publicly reachable at: ${APP_URL}"

            DESIRED_URL="${APP_URL%/}/github-webhook/"
            echo "Desired GitHub webhook URL: ${DESIRED_URL}"

            GH_API="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/hooks"
            AUTHH="Authorization: token ${GITHUB_TOKEN}"
            ACH="Accept: application/vnd.github.v3+json"
            CT="Content-Type: application/json"

            # 3) Fetch existing hooks
            HOOKS_JSON="$(curl -fsSL -H "$AUTHH" -H "$ACH" "$GH_API" || echo "[]")"

            # 4) Find an existing 'web' hook pointing to /github-webhook/
            HOOK_ID="$(${PY3} - <<PY
import json,sys
data=json.loads("""${HOOKS_JSON}""")
for h in data:
  cfg=h.get("config") or {}
  url=cfg.get("url") or ""
  if url.endswith("/github-webhook/"):
    print(h.get("id") or "")
    break
PY
)"
            if [ -n "${HOOK_ID}" ]; then
              echo "Existing webhook found: ID=${HOOK_ID}. Ensuring URL/config up to date..."
              curl -fsSL -X PATCH "$GH_API/${HOOK_ID}" \
                -H "$AUTHH" -H "$ACH" -H "$CT" \
                -d @- <<JSON >/dev/null
{
  "active": true,
  "events": ["push"],
  "config": {
    "url": "${DESIRED_URL}",
    "content_type": "json",
    "insecure_ssl": "0"
  }
}
JSON
            else
              echo "No existing webhook. Creating a new one..."
              curl -fsSL -X POST "$GH_API" \
                -H "$AUTHH" -H "$ACH" -H "$CT" \
                -d @- <<JSON >/dev/null
{
  "name": "web",
  "active": true,
  "events": ["push"],
  "config": {
    "url": "${DESIRED_URL}",
    "content_type": "json",
    "insecure_ssl": "0"
  }
}
JSON
            fi

            echo "GitHub webhook is set to: ${DESIRED_URL}"
          '''
        }
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
          echo "Using docker at: ${DOCKER}"
          ${DOCKER} build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:latest .
        '''
      }
    }

    stage('Push to Docker Hub') {
      steps {
        sh '''
          set -e
          echo $DOCKERHUB_PSW | ${DOCKER} login -u $DOCKERHUB_USR --password-stdin
          ${DOCKER} push ${IMAGE_NAME}:${BUILD_NUMBER}
          ${DOCKER} push ${IMAGE_NAME}:latest
        '''
      }
    }

    stage('Deploy via Ansible') {
      steps {
        sh '''
          set -e

          ANS_VENV=".ansible-venv"
          if [ ! -d "${ANS_VENV}" ]; then
            ${PY3} -m venv ${ANS_VENV}
          fi
          . ${ANS_VENV}/bin/activate
          python -m pip install --upgrade pip
          pip install "ansible>=9" requests docker packaging
          ansible-galaxy collection install community.docker --force

          ANSIBLE_PY="$(pwd)/${ANS_VENV}/bin/python"
          "$(pwd)/${ANS_VENV}/bin/ansible-playbook" \
            -i deploy/hosts.ini \
            deploy/deploy.yml \
            --extra-vars "image=${IMAGE_NAME}:latest container_name=spe-calc app_port=5000 ansible_python_interpreter=${ANSIBLE_PY}"
        '''
      }
    }
  }
}


