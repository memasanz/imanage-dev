// =============================================================================
// API Management — Standard v2, private.
//
// Public network access disabled, inbound private endpoint (groupId 'gateway'),
// outbound VNet integration (snet-apim). Hosts the five fine-grained APIs
// (models, agents, iManage Work, iManage MCP, iManage OAuth) with named
// operations for per-call telemetry, and the policy XML under docs/apim/policies.
//
// NOTE: Standard v2 provisions slowly. If a first-time apply fails on the
// publicNetworkAccess/private-endpoint ordering, set apimPublicNetworkAccess
// to 'Enabled' for the initial apply, then re-run with 'Disabled'.
// =============================================================================

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('APIM service name.')
param apimName string

@description('Publisher email (required by APIM).')
param publisherEmail string = 'admin@example.com'

@description('Publisher org name.')
param publisherName string = 'iManage AI Workspace'

@description('User-assigned identity resource id for APIM.')
param userAssignedIdentityId string

@description('Subnet id for outbound VNet integration (snet-apim).')
param vnetIntegrationSubnetId string

@description('Subnet id for the inbound private endpoint.')
param privateEndpointSubnetId string

@description('Private DNS zone id for privatelink.azure-api.net.')
param privateDnsZoneId string

@description('Public network access. Disabled = private only (requires the PE below).')
@allowed([ 'Enabled', 'Disabled' ])
param apimPublicNetworkAccess string = 'Disabled'

// --- Backend service URLs (per surface) ------------------------------------
@description('Foundry models endpoint (OpenAI-compatible).')
param foundryModelsUrl string = 'https://placeholder.openai.azure.com'

@description('Foundry agents (Agent Service) endpoint.')
param foundryAgentsUrl string = 'https://placeholder.services.ai.azure.com'

@description('iManage Work REST base url (mock upstream or cloudimanage.com).')
param imanageWorkUrl string

@description('iManage MCP base url.')
param imanageMcpUrl string

@description('iManage OAuth token host.')
param imanageOauthUrl string

// --- Named-value inputs ----------------------------------------------------
@description('Same-origin SPA host for CORS (https://<appservice-host>).')
param spaOrigin string

@description('mock | live — exposed to policies.')
param imanageBackendMode string

@description('iManage subscription key (secret; inject real value post-deploy or via KV).')
@secure()
param imanageSubscriptionKey string = ''

@description('iManage Work OAuth client secret (secret).')
@secure()
param workClientSecret string = ''

@description('iManage MCP OAuth client secret (secret).')
@secure()
param mcpClientSecret string = ''

@description('Allowed OAuth redirect URIs (comma-separated).')
param redirectUriAllowlist string = ''

resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: apimName
  location: location
  tags: tags
  sku: {
    name: 'StandardV2'
    capacity: 1
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    publicNetworkAccess: apimPublicNetworkAccess
    virtualNetworkType: 'External'
    virtualNetworkConfiguration: {
      subnetResourceId: vnetIntegrationSubnetId
    }
  }
}

// --- Named values ----------------------------------------------------------
var namedValues = [
  { name: 'spa-origin', value: spaOrigin, secret: false }
  { name: 'imanage-backend-mode', value: imanageBackendMode, secret: false }
  { name: 'imanage-work-auth-base-url', value: imanageOauthUrl, secret: false }
  { name: 'imanage-mcp-auth-base-url', value: imanageMcpUrl, secret: false }
  { name: 'redirect-uri-allowlist', value: redirectUriAllowlist, secret: false }
  { name: 'imanage-subscription-key', value: imanageSubscriptionKey, secret: true }
  { name: 'work-client-secret', value: workClientSecret, secret: true }
  { name: 'mcp-client-secret', value: mcpClientSecret, secret: true }
]

resource nv 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = [
  for item in namedValues: {
    parent: apim
    name: item.name
    properties: {
      displayName: item.name
      value: empty(item.value) ? '-' : item.value
      secret: item.secret
    }
  }
]

// --- APIs + operations -----------------------------------------------------
var apiDefs = [
  {
    name: 'models'
    displayName: 'Models (Foundry)'
    path: 'models'
    serviceUrl: foundryModelsUrl
    policyFile: loadTextContent('../../docs/apim/policies/models-agents.xml')
    operations: [
      { name: 'chat-completions', method: 'POST', url: '/chat/completions', display: 'Chat completions', params: [] }
      { name: 'responses', method: 'POST', url: '/responses', display: 'Responses', params: [] }
      { name: 'embeddings', method: 'POST', url: '/embeddings', display: 'Embeddings', params: [] }
    ]
  }
  {
    name: 'agents'
    displayName: 'Agents (Foundry Agent Service)'
    path: 'agents'
    serviceUrl: foundryAgentsUrl
    policyFile: loadTextContent('../../docs/apim/policies/models-agents.xml')
    operations: [
      { name: 'create-thread', method: 'POST', url: '/threads', display: 'Create thread', params: [] }
      { name: 'run-turn', method: 'POST', url: '/threads/runs', display: 'Run turn', params: [] }
      { name: 'get-run', method: 'GET', url: '/threads/{threadId}/runs/{runId}', display: 'Get run', params: [ 'threadId', 'runId' ] }
      { name: 'list-messages', method: 'GET', url: '/threads/{threadId}/messages', display: 'List messages', params: [ 'threadId' ] }
    ]
  }
  {
    name: 'imanage-work'
    displayName: 'iManage Work'
    path: 'imanage/work'
    serviceUrl: imanageWorkUrl
    policyFile: loadTextContent('../../docs/apim/policies/imanage-work-mcp.xml')
    operations: [
      { name: 'documents-search', method: 'POST', url: '/customers/{customerId}/documents/search', display: 'Documents search', params: [ 'customerId' ] }
      { name: 'document-get', method: 'GET', url: '/customers/{customerId}/documents/{id}', display: 'Document get', params: [ 'customerId', 'id' ] }
      { name: 'document-versions', method: 'GET', url: '/customers/{customerId}/documents/{id}/versions', display: 'Document versions', params: [ 'customerId', 'id' ] }
      { name: 'document-text', method: 'GET', url: '/customers/{customerId}/documents/{id}/text', display: 'Document text', params: [ 'customerId', 'id' ] }
      { name: 'workspaces-search', method: 'GET', url: '/customers/{customerId}/workspaces', display: 'Workspaces search', params: [ 'customerId' ] }
      { name: 'workspace-children', method: 'GET', url: '/customers/{customerId}/workspaces/{id}/children', display: 'Workspace children', params: [ 'customerId', 'id' ] }
      { name: 'folders-search', method: 'GET', url: '/customers/{customerId}/folders/search', display: 'Folders search', params: [ 'customerId' ] }
      { name: 'folder-children', method: 'GET', url: '/customers/{customerId}/folders/{id}/children', display: 'Folder children', params: [ 'customerId', 'id' ] }
      { name: 'clients-search', method: 'GET', url: '/customers/{customerId}/clients/search', display: 'Clients search', params: [ 'customerId' ] }
      { name: 'users-search', method: 'GET', url: '/customers/{customerId}/users/search', display: 'Users search', params: [ 'customerId' ] }
      { name: 'users-me', method: 'GET', url: '/customers/{customerId}/users/me', display: 'Users me', params: [ 'customerId' ] }
      { name: 'libraries', method: 'GET', url: '/customers/{customerId}/libraries', display: 'Libraries', params: [ 'customerId' ] }
    ]
  }
  {
    name: 'imanage-mcp'
    displayName: 'iManage MCP'
    path: 'imanage/mcp'
    serviceUrl: imanageMcpUrl
    policyFile: loadTextContent('../../docs/apim/policies/imanage-work-mcp.xml')
    operations: [
      { name: 'rpc', method: 'POST', url: '/', display: 'JSON-RPC (initialize/search/fetch/call-tool)', params: [] }
    ]
  }
  {
    name: 'imanage-oauth'
    displayName: 'iManage OAuth'
    path: 'imanage/oauth'
    serviceUrl: imanageOauthUrl
    policyFile: loadTextContent('../../docs/apim/policies/imanage-oauth.xml')
    operations: [
      { name: 'token', method: 'POST', url: '/token', display: 'Token exchange', params: [] }
      { name: 'refresh', method: 'POST', url: '/refresh', display: 'Token refresh', params: [] }
    ]
  }
]

module apiModules 'apim-api.bicep' = [
  for api in apiDefs: {
    name: 'apim-api-${api.name}'
    params: {
      apimName: apim.name
      apiName: api.name
      displayName: api.displayName
      path: api.path
      serviceUrl: api.serviceUrl
      operations: api.operations
      policyXml: api.policyFile
    }
    dependsOn: [
      nv
    ]
  }
]

// --- Service-scope global policy -------------------------------------------
resource servicePolicy 'Microsoft.ApiManagement/service/policies@2023-05-01-preview' = {
  parent: apim
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('../../docs/apim/policies/global.xml')
  }
  dependsOn: [
    nv
  ]
}

// --- Inbound private endpoint ----------------------------------------------
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${apimName}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${apimName}'
        properties: {
          privateLinkServiceId: apim.id
          groupIds: [
            'Gateway'
          ]
        }
      }
    ]
  }
}

resource dnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'gateway'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

@description('APIM resource id.')
output apimId string = apim.id

@description('APIM gateway URL (private).')
output gatewayUrl string = apim.properties.gatewayUrl

@description('APIM service name.')
output apimServiceName string = apim.name
