#!/usr/bin/env bash
# =============================================================================
# deploy_advisor.sh — Build, push, and deploy the advisor-agent to Azure
#
# USAGE:
#   bash scripts/deploy_advisor.sh
#
# ENVIRONMENT VARIABLES:
#   TAG              Docker image tag to build and deploy (default: latest)
#   RESOURCE_GROUP   Azure resource group containing the Web App
#                    (default: rg-hack-trial)
#
# EXAMPLE:
#   TAG=1.2.0 RESOURCE_GROUP=rg-prod bash scripts/deploy_advisor.sh
#
# PREREQUISITES:
#   - Azure CLI (az) installed and logged in   https://aka.ms/installazurecli
#   - Docker installed and daemon running       https://docs.docker.com/get-docker/
# =============================================================================
set -euo pipefail

# --- Prerequisites check ---
for cmd in az docker; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' is not installed or not in PATH. Aborting." >&2
    exit 1
  fi
done

ACR_NAME="hacklondon"
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
IMAGE_NAME="advisor-agent"
TAG="${TAG:-latest}"
FULL_IMAGE="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${TAG}"
WEBAPP_NAME="weba-hosbi-advisor-hack-london"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-hack-trial}"

echo "Building advisor-agent image: ${FULL_IMAGE}"
docker build \
  --tag "${FULL_IMAGE}" \
  --file advisor/agents/advisor_agent/Dockerfile \
  .

echo "Logging in to ACR: ${ACR_LOGIN_SERVER}"
az acr login --name "${ACR_NAME}"

echo "Pushing image: ${FULL_IMAGE}"
docker push "${FULL_IMAGE}"

echo "Updating web app '${WEBAPP_NAME}' to image '${FULL_IMAGE}'"
az webapp config container set \
  --name "${WEBAPP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --container-image-name "${FULL_IMAGE}"

echo "Restarting web app '${WEBAPP_NAME}'"
az webapp restart \
  --name "${WEBAPP_NAME}" \
  --resource-group "${RESOURCE_GROUP}"

echo "Done. '${WEBAPP_NAME}' is now running ${FULL_IMAGE}"
