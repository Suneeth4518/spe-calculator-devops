pipeline {
  agent any

  environment {
    IMAGE_NAME = "suneeth4518/spe-calculator"
    DOCKERHUB  = credentials('dockerhub-creds')
    PY3        = "/opt/homebrew/bin/python3"
    ANSIBLE    = "/opt/homebrew/bin/ansible-playbook"

    // --- NEW ---
    NGROK_BIN  = "/opt/homebrew/bin/ngrok"   // adjust if different
    GH_TOKEN   = credentials('github-token')
    GH_OWNER   = "Suneeth4518"
    GH_REPO    = "spe-calculator-devops"

    // Your static dev domain that points to Jenkins:8080
    JENKINS_NGROK = "https://gullibly-clinometric-demi.ngrok-free.dev"
  }

  triggers { githubPush() }

  stages {
    stage('Checkout') {
      steps { checkout scm }
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
      post { always { junit 'reports/pytest.xml' } }
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
          set -e
          if ! /opt/homebrew/bin/ansible-galaxy collection list | grep -q community.docker; then
            /opt/homebrew/bin/ansible-galaxy collection install community.docker
          fi

          ${ANSIBLE} -i deploy/hosts.ini deploy/deploy.yml \
            --extra-vars "image=${IMAGE_NAME}:latest container_name=spe-calc app_port=5000"
        '''
      }
    }

    // --- NEW STAGE ---
    stage('Expose & Update Webhooks') {
      steps {
        sh '''
          set -e

          # 1) Start/Restart ngrok for the APP on port 5000 (random URL).
          #    We keep the static dev domain reserved for Jenkins webhook.
          if pgrep -f "${NGROK_BIN} http 5000" >/dev/null 2>&1; then
            pkill -f "${NGROK_BIN} http 5000" || true
            sleep 1
          fi

          nohup ${NGROK_BIN} http 5000 --log=stdout > ngrok_app.log 2>&1 &

          # Wait a moment for the local ngrok API
          for i in $(seq 1 20); do
            if curl -fsS http://127.0.0.1:4040/api/tunnels >/dev/null 2>&1; then break; fi
            sleep 0.5
          done

          # Grab the public URL for the app (first https tunnel)
          APP_URL=$(${PY3} - <<'PY'
import json,urllib.request,sys
try:
    data=json.load(urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels'))
    urls=[t['public_url'] for t in data.get('tunnels',[]) if t.get('proto')=='https']
    print(urls[0] if urls else '')
except Exception as e:
    print('', end='')
PY
)
          if [ -z "$APP_URL" ]; then
            echo "WARNING: Could not fetch app ngrok URL from 4040 API"
          else
            echo "App is publicly reachable at: $APP_URL"
          fi

          # 2) Upsert GitHub webhook -> Jenkins static domain /github-webhook/
          DESIRED_URL="${JENKINS_NGROK}/github-webhook/"

          # Try to find existing webhook pointing to our domain
          HOOK_ID=$(curl -fsSL -H "Authorization: token ${GH_TOKEN}" \
            https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/hooks \
            | ${PY3} - <<'PY'
import json,sys,os
import re
data=json.load(sys.stdin)
target=os.environ.get("DESIRED_URL","")
for h in data:
    cfg=h.get("config",{})
    if (cfg.get("url")==target):
        print(h.get("id"))
        break
PY
)
          if [ -n "$HOOK_ID" ]; then
            echo "Updating existing webhook ($HOOK_ID) -> $DESIRED_URL"
            curl -fsSL -X PATCH \
              -H "Authorization: token ${GH_TOKEN}" \
              -H "Content-Type: application/json" \
              -d "{\"config\":{\"url\":\"${DESIRED_URL}\",\"content_type\":\"json\",\"insecure_ssl\":\"0\"},\"active\":true}" \
              https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/hooks/${HOOK_ID} >/dev/null
          else
            echo "Creating new webhook -> $DESIRED_URL"
            curl -fsSL -X POST \
              -H "Authorization: token ${GH_TOKEN}" \
              -H "Content-Type: application/json" \
              -d "{\"name\":\"web\",\"active\":true,\"events\":[\"push\",\"pull_request\"],\"config\":{\"url\":\"${DESIRED_URL}\",\"content_type\":\"json\",\"insecure_ssl\":\"0\"}}" \
              https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/hooks >/dev/null
          fi

          echo "GitHub webhook now points to: $DESIRED_URL"
        '''
      }
    }
  }
}
