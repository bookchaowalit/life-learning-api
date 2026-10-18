import { defineRailway, project, service } from "railway/iac";

// life-learning-api: the Learning cell. Variables stay unmanaged (secrets live in Railway only).
// learning-api sleeps when idle (Railway Serverless) and wakes on the next request.
// Every service runs in Singapore next to Neon (aws-ap-southeast-1) and empire-platform; the IaC does not
// carry the region, so after the first deploy: railway scale --service <svc> asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0
// Every service deploys from GitHub main after CI passes (Railway Wait for CI, 2026-10-18).
// Declared here so `railway config apply` keeps the connection instead of removing it.
const github = {
  type: "github" as const,
  repo: "bookchaowalit/life-learning-api",
  branch: "main",
  checkSuites: true,
};

export default defineRailway(() => {
  const api = service("learning-api", {
    source: github,
    healthcheck: "/health",
    healthcheckTimeout: 60,
    deploy: { sleepApplication: true },
  });

  return project("life-learning-api", {
    variables: { managed: false },
    resources: [api],
  });
});
