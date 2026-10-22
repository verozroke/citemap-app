# Jenkins for CiteMap

A local Jenkins controller, configured as code, that runs the pipeline in
[`../Jenkinsfile`](../Jenkinsfile) against this repository.

## What you get

- Jenkins LTS (JDK 21) with the Docker CLI and the plugins in `plugins.txt`.
- No setup wizard: the admin user, an optional Docker Hub credential and the
  pipeline job `citemap-app` are created from `casc.yaml` on first start.
- The pipeline uses the Docker engine of the host through the mounted socket.

## Start

Requirements: Docker Desktop (Windows, macOS) or Docker Engine (Linux).

```bash
cd jenkins
cp .env.example .env          # Windows: copy .env.example .env
# edit .env: set JENKINS_ADMIN_PASSWORD (and Docker Hub values if you want to push)
docker compose up -d --build
```

Open <http://localhost:8080> and sign in with the admin user from `.env`.
The first build takes 5 to 10 minutes because Docker downloads the base images
and the dependencies; later builds reuse the cached layers.

## Use

1. Open the job **CiteMap CI/CD** and press **Build Now**. The first build also
   registers the polling trigger and the build parameters.
2. Watch the stages in **Pipeline Overview** (Pipeline Graph View) or the Stage
   View on the job page. Test results and backend coverage appear on the build page.
3. Push a commit to `main`. Jenkins checks GitHub every two minutes and starts a
   new build for the commit.
4. After a successful build the application runs as the staging container at
   <http://localhost:8081>.

### Optional: push to Docker Hub

Create an access token at hub.docker.com (Account settings, Personal access
tokens), put `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` into `.env`, run
`docker compose up -d` again, then start **Build with Parameters** with
`PUSH_IMAGE` checked and your repository in `DOCKERHUB_REPO`.

## Stop or reset

```bash
docker compose down            # stop Jenkins, keep its data
docker compose down -v         # also delete the Jenkins home volume
docker rm -f citemap-staging   # stop the staging deployment
```

## Notes

- The controller runs as root so that it can use the Docker socket on Docker
  Desktop. This is fine for a local lab; a shared server should use a separate
  build agent and a Docker group instead.
- A local Jenkins cannot receive GitHub webhooks, so the job polls GitHub. If
  Jenkins is reachable from the internet, add a webhook and replace `pollSCM`
  with `githubPush()` in the Jenkinsfile.
- Every stage is a script in `ci/`. Without Jenkins, `ci/run-local.sh --deploy`
  runs the same steps on any machine with Docker and Bash.
