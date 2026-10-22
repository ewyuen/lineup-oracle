// One Container App with the shared identity. Used for both the API (internal) and the UI (public).
param name string
param location string
param environmentId string
param identityId string
param registryServer string
param image string
param targetPort int
param externalIngress bool
param env array = []

@secure()
@description('Postgres URL of the player-history graph, kept as the Container Apps secret `pg-url`. Empty: no secret.')
param graphUrl string = ''

@description('HTTP probes on /health. Off for the placeholder image, which does not serve it.')
param healthProbe bool = false

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: empty(graphUrl) ? [] : [
        { name: 'pg-url', value: graphUrl }
      ]
      ingress: {
        external: externalIngress
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: registryServer
          identity: identityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: name
          image: image
          env: env
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: healthProbe ? [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: targetPort }
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: targetPort }
              periodSeconds: 10
            }
          ] : []
        }
      ]
      // One replica: team news is held in memory per session, and the UI keeps its anti-forgery keys in memory.
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
