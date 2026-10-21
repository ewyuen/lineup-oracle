// Lineup Oracle on Azure: monitoring, registry, Container Apps environment and a shared identity.
targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short prefix for resource names (lowercase letters and digits).')
@minLength(2)
@maxLength(12)
param namePrefix string = 'lineup'

@description('API image tag in the registry. Empty deploys a public placeholder image (first pass).')
param apiImageTag string = ''

@description('UI image tag in the registry. Empty deploys a public placeholder image (first pass).')
param uiImageTag string = ''

@description('Model to deploy.')
param modelName string = 'gpt-4.1-mini'

@description('Model version.')
param modelVersion string = '2025-04-14'

@description('Deployment SKU.')
param modelSkuName string = 'GlobalStandard'

@description('Deployment capacity in thousands of tokens per minute.')
param modelCapacity int = 30

@description('Existing model endpoint. When set together with existingLlmDeployment, no Foundry account is created.')
param existingLlmEndpoint string = ''

@description('Existing model deployment name (used with existingLlmEndpoint).')
param existingLlmDeployment string = ''

var suffix = uniqueString(resourceGroup().id)
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
var foundryName = '${namePrefix}-foundry-${suffix}'
var useExistingLlm = !empty(existingLlmEndpoint) && !empty(existingLlmDeployment)

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs-${suffix}'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-ai-${suffix}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${namePrefix}acr${suffix}'
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-${suffix}'
  location: location
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, acrPullRoleId)
  scope: registry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-env-${suffix}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

// Created only when no existing endpoint is given. Local (key) auth is off: callers use Entra ID.
resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = if (!useExistingLlm) {
  name: foundryName
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: foundryName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource model 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (!useExistingLlm) {
  parent: foundry
  name: modelName
  sku: {
    name: modelSkuName
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
  }
}

resource openAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingLlm) {
  name: guid(foundry.id, identity.id, openAiUserRoleId)
  scope: foundry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
  }
}

var llmEndpoint = useExistingLlm ? existingLlmEndpoint : 'https://${foundryName}.openai.azure.com/'
var llmDeployment = useExistingLlm ? existingLlmDeployment : modelName

var placeholderImage = 'mcr.microsoft.com/k8se/quickstart:latest' // listens on port 80
var apiReal = !empty(apiImageTag)
var uiReal = !empty(uiImageTag)

module api 'containerApp.bicep' = {
  name: 'api'
  params: {
    name: '${namePrefix}-api'
    location: location
    environmentId: environment.id
    identityId: identity.id
    registryServer: registry.properties.loginServer
    image: apiReal ? '${registry.properties.loginServer}/lineup-api:${apiImageTag}' : placeholderImage
    targetPort: apiReal ? 8000 : 80
    externalIngress: false
    healthProbe: apiReal
    env: [
      { name: 'OTEL_SERVICE_NAME', value: 'lineup-api' }
      { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.properties.ConnectionString }
      { name: 'LINEUP_LLM_ENDPOINT', value: llmEndpoint }
      { name: 'LINEUP_LLM_DEPLOYMENT', value: llmDeployment }
      // Tells DefaultAzureCredential which user-assigned identity to use.
      { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
    ]
  }
  dependsOn: [
    acrPull
    openAiUser
  ]
}

module ui 'containerApp.bicep' = {
  name: 'ui'
  params: {
    name: '${namePrefix}-ui'
    location: location
    environmentId: environment.id
    identityId: identity.id
    registryServer: registry.properties.loginServer
    image: uiReal ? '${registry.properties.loginServer}/lineup-ui:${uiImageTag}' : placeholderImage
    targetPort: uiReal ? 8080 : 80
    externalIngress: true
    env: [
      { name: 'OTEL_SERVICE_NAME', value: 'lineup-ui' }
      { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.properties.ConnectionString }
      { name: 'LineupApi__BaseUrl', value: 'https://${api.outputs.fqdn}' }
    ]
  }
  dependsOn: [
    acrPull
  ]
}

output uiUrl string = 'https://${ui.outputs.fqdn}'
output llmEndpoint string = llmEndpoint
output llmDeployment string = llmDeployment
output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
output appInsightsConnectionString string = insights.properties.ConnectionString
