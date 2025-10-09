pipeline {
  agent any
  environment {
    IMAGE_NAME = "suneeth4518/spe-calculator"
    DOCKERHUB = credentials('dockerhub-creds')
  }
  triggers { githubPush() }
  stages {
    stage('Checkout'){steps{checkout scm}}
    stage('Test'){steps{sh 'pip install -r requirements.txt'; sh 'pytest -q'}}
    stage('Build'){steps{sh 'docker build -t $IMAGE_NAME:latest .'}}
    stage('Push'){steps{sh 'echo $DOCKERHUB_PSW | docker login -u $DOCKERHUB_USR --password-stdin'; sh 'docker push $IMAGE_NAME:latest'}}
    stage('Deploy'){steps{sh 'ansible-playbook -i deploy/hosts.ini deploy/deploy.yml'}}
  }
}
