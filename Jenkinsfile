// CI/CD pipeline for CiteMap (Assignment 5).
// Every stage calls a script in ci/, so the same steps can be run on a laptop
// with ci/run-local.sh. Jenkins drives the host's Docker engine.
pipeline {
    agent any

    options {
        timestamps()
        ansiColor('xterm')
        timeout(time: 45, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }

    triggers {
        // Check GitHub for new commits every two minutes, so each commit to main
        // starts a build. A webhook can replace polling when Jenkins is reachable
        // from the internet.
        pollSCM('H/2 * * * *')
    }

    parameters {
        booleanParam(name: 'DEPLOY_STAGING', defaultValue: true,
                     description: 'Deploy the new image to the staging container (port 8081)')
        booleanParam(name: 'PUSH_IMAGE', defaultValue: false,
                     description: 'Push the image to Docker Hub (needs the dockerhub credential)')
        string(name: 'DOCKERHUB_REPO', defaultValue: 'verozroke/citemap-app',
               description: 'Docker Hub repository for the optional push')
    }

    environment {
        IMAGE_NAME = 'citemap-app'
        STAGING_PORT = '8081'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'rm -rf reports'
                script {
                    env.GIT_COMMIT = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_COMMIT.substring(0, 7)}"
                    currentBuild.description = "image ${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                }
                sh 'git log -1 --format="Commit %h by %an: %s"'
                sh 'docker version --format "Docker engine {{.Server.Version}}"'
            }
        }

        stage('Unit tests') {
            parallel {
                stage('Backend') {
                    steps {
                        sh 'ci/test-backend.sh'
                    }
                    post {
                        always {
                            junit testResults: 'reports/backend-junit.xml', allowEmptyResults: true
                            recordCoverage tools: [[parser: 'COBERTURA', pattern: 'reports/backend-coverage.xml']],
                                           sourceCodeRetention: 'NEVER'
                        }
                    }
                }
                stage('Frontend') {
                    steps {
                        sh 'ci/test-frontend.sh'
                    }
                    post {
                        always {
                            junit testResults: 'reports/frontend-junit.xml', allowEmptyResults: true
                        }
                    }
                }
            }
        }

        stage('Build image') {
            steps {
                sh 'ci/build-image.sh'
            }
        }

        stage('Smoke test') {
            steps {
                sh 'ci/smoke-test.sh'
            }
        }

        stage('Push to Docker Hub') {
            when {
                expression { params.PUSH_IMAGE }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                                  usernameVariable: 'DOCKERHUB_USERNAME',
                                                  passwordVariable: 'DOCKERHUB_TOKEN')]) {
                    withEnv(["DOCKERHUB_REPO=${params.DOCKERHUB_REPO}"]) {
                        sh 'ci/push-image.sh'
                    }
                }
            }
        }

        stage('Deploy to staging') {
            when {
                expression { params.DEPLOY_STAGING }
            }
            steps {
                sh 'ci/deploy-staging.sh'
            }
        }
    }

    post {
        success {
            echo "Build ${env.IMAGE_TAG} passed. Staging: http://localhost:${env.STAGING_PORT}"
        }
        always {
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
            sh 'ci/cleanup.sh || true'
        }
    }
}
