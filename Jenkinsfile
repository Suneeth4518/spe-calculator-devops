pipeline {
  agent any

  environment {
    IMAGE_NAME = "suneeth4518/spe-calculator"
    DOCKERHUB = credentials('dockerhub-creds')
    PY3 = "/opt/homebrew/bin/python3"
    ANSIBLE = "/opt/homebrew/bin/ansible-playbook"
    ANSIBLE_VENV = "${HOME}/.ansible-venv"
  }

  triggers { githubPush() }

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
        always {
          junit 'reports/pytest.xml'
        }
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
          set -e

          echo "=== Ensuring Ansible venv exists and has required packages ==="
          if [ ! -x "${ANSIBLE_VENV}/bin/python" ]; then
            echo "Creating Ansible venv at ${ANSIBLE_VENV}"
            ${PY3} -m venv "${ANSIBLE_VENV}"
            "${ANSIBLE_VENV}/bin/python" -m pip install --upgrade pip
          fi

          echo "Installing Ansible Python dependencies..."
          "${ANSIBLE_VENV}/bin/pip" install --upgrade packaging requests docker

          echo "=== Ensuring Ansible community.docker collection is installed ==="
          if ! /opt/homebrew/bin/ansible-galaxy collection list | grep -q community.docker; then
            /opt/homebrew/bin/ansible-galaxy collection install community.docker
          fi

          echo "=== Running Ansible Playbook ==="
          ${ANSIBLE} -i deploy/hosts.ini deploy/deploy.yml \
            --extra-vars "image=${IMAGE_NAME}:latest container_name=spe-calc app_port=5000"
        '''
      }
    }
  }
}
