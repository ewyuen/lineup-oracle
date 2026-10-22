using './main.bicep'

param namePrefix = 'lineup'
param modelName = 'gpt-4.1-mini'
param modelVersion = '2025-04-14'
param modelSkuName = 'GlobalStandard'
param modelCapacity = 30

// Set by deploy.ps1. Empty tags deploy a placeholder image (first pass).
param apiImageTag = readEnvironmentVariable('API_IMAGE_TAG', '')
param uiImageTag = readEnvironmentVariable('UI_IMAGE_TAG', '')

// No-quota option: point at a model you already have (see infra/README.md). Empty creates a new account.
param existingLlmEndpoint = readEnvironmentVariable('EXISTING_LLM_ENDPOINT', '')
param existingLlmDeployment = readEnvironmentVariable('EXISTING_LLM_DEPLOYMENT', '')

// Optional player-history graph (Postgres + Apache AGE). Off unless GRAPH_ADMIN_PASSWORD is set; see infra/README.md.
param graphAdminPassword = readEnvironmentVariable('GRAPH_ADMIN_PASSWORD', '')
param enableHistoryGraph = !empty(graphAdminPassword)
