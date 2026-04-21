# Deploy `adabtech` to Cloud Run from GitHub Actions (WIF)

This repository includes `.github/workflows/deploy-cloud-run.yml` to deploy Cloud Run service `adabtech` on push to `main`.

## Target runtime

- **Project ID:** `gen-lang-client-0675423068`
- **Project Number:** `1015422054034`
- **Cloud Run Service:** `adabtech`
- **Region:** `europe-west1`
- **URL:** `https://adabtech-1015422054034.europe-west1.run.app`
- **Deploy env vars:**
  - `VERTEX_PROJECT_ID=gen-lang-client-0675423068`
  - `VERTEX_LOCATION=europe-west1`

## Required GitHub repository variables

Add these repository variables in **GitHub → Settings → Secrets and variables → Actions → Variables**:

- `GCP_WIF_PROVIDER`
  - Value format:
    `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID`
  - Example placeholder:
    `projects/1015422054034/locations/global/workloadIdentityPools/<POOL_ID>/providers/<PROVIDER_ID>`
- `GCP_SERVICE_ACCOUNT`
  - Value format: service account email
  - Example placeholder:
    `<DEPLOYER_SA_NAME>@gen-lang-client-0675423068.iam.gserviceaccount.com`

> No long-lived service account JSON key is required.

## One-time GCP setup (Workload Identity Federation)

Set shell variables first:

```bash
PROJECT_ID="gen-lang-client-0675423068"
PROJECT_NUMBER="1015422054034"
REGION="europe-west1"
REPO_OWNER="adab-tech"
REPO_NAME="hausa-ai"
POOL_ID="<POOL_ID>"
PROVIDER_ID="<PROVIDER_ID>"
DEPLOYER_SA_NAME="<DEPLOYER_SA_NAME>"
DEPLOYER_SA="${DEPLOYER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
AR_REPOSITORY="adabtech"
```

### 1) Enable required APIs

```bash
gcloud services enable \
  iamcredentials.googleapis.com \
  iam.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### 2) Create Artifact Registry repository (if it does not exist)

```bash
gcloud artifacts repositories create "${AR_REPOSITORY}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Images for adabtech Cloud Run deploy"
```

### 3) Create deployer service account

```bash
gcloud iam service-accounts create "${DEPLOYER_SA_NAME}" \
  --display-name="GitHub Actions Cloud Run deployer"
```

### 4) Grant IAM roles to deployer service account

```bash
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/iam.serviceAccountUser"
```

### 5) Create Workload Identity Pool + OIDC provider

```bash
gcloud iam workload-identity-pools create "${POOL_ID}" \
  --location="global" \
  --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" \
  --display-name="GitHub OIDC Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref"
```

### 6) Allow this GitHub repo to impersonate the deployer service account

```bash
WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

gcloud iam service-accounts add-iam-policy-binding "${DEPLOYER_SA}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WIF_PROVIDER}/attribute.repository/${REPO_OWNER}/${REPO_NAME}"
```

## Deploy flow

On every push to `main`, the workflow will:

1. Authenticate to Google Cloud using WIF (`google-github-actions/auth`).
2. Build Docker image from `backend/Dockerfile`.
3. Push image to Artifact Registry.
4. Deploy/update Cloud Run service `adabtech` in `europe-west1`.
5. Set required environment variables:
   - `VERTEX_PROJECT_ID=gen-lang-client-0675423068`
   - `VERTEX_LOCATION=europe-west1`
