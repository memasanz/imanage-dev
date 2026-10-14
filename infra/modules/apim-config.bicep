// =============================================================================
// APIM configuration (BYO APIM) — Sprint 1, iManage MCP tool only.
//
// References an EXISTING API Management instance (brought by the customer via
// .env). The customer's models/agents (responses) APIs already route through
// this APIM, so this module registers ONLY the fine-grained iManage MCP route
// that the Foundry hosted agent uses as its MCP tool, plus its policy and the
// single named value the policy needs.
//
// It does NOT create APIM and does NOT touch the service-level global policy.
// Deploy this module scoped to the APIM's resource group.
// =============================================================================

@description('Existing APIM service name.')
param apimName string

@description('iManage MCP base url the route forwards to (mock upstream or cloudimanage.com/mcp).')
param imanageMcpUrl string

@description('iManage Work API base url the route forwards to (mock upstream /work/api/v2 or {tenant}.cloudimanage.com/work/api/v2).')
param imanageWorkUrl string

@description('iManage subscription key the MCP policy presents to the upstream (secret).')
@secure()
param imanageSubscriptionKey string = ''

resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' existing = {
  name: apimName
}

// Named value referenced by the MCP policy ({{imanage-subscription-key}}).
resource subscriptionKeyNv 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'imanage-subscription-key'
  properties: {
    displayName: 'imanage-subscription-key'
    value: empty(imanageSubscriptionKey) ? '-' : imanageSubscriptionKey
    secret: true
  }
}

// iManage MCP API: single JSON-RPC endpoint, fine-grained logging via the policy.
module mcpApi 'apim-api.bicep' = {
  name: 'apim-api-imanage-mcp'
  params: {
    apimName: apim.name
    apiName: 'imanage-mcp'
    displayName: 'iManage MCP'
    path: 'imanage/mcp'
    serviceUrl: imanageMcpUrl
    operations: [
      { name: 'rpc', method: 'POST', url: '/', display: 'JSON-RPC (initialize/search/fetch/call-tool)', params: [] }
    ]
    policyXml: loadTextContent('../../docs/apim/policies/imanage-work-mcp.xml')
  }
  dependsOn: [
    subscriptionKeyNv
  ]
}

// iManage Work REST API: fine-grained operations so every upstream Work call is
// individually visible in APIM metrics/logs. Same policy as MCP (branches on Api.Id).
module workApi 'apim-api.bicep' = {
  name: 'apim-api-imanage-work'
  params: {
    apimName: apim.name
    apiName: 'imanage-work'
    displayName: 'iManage Work'
    path: 'imanage/work'
    serviceUrl: imanageWorkUrl
    operations: [
      { name: 'libraries', method: 'GET', url: '/customers/{customerId}/libraries', display: 'List libraries', params: [ 'customerId' ] }
      { name: 'documents-search', method: 'POST', url: '/customers/{customerId}/documents/search', display: 'Search documents', params: [ 'customerId' ] }
      { name: 'document-get', method: 'GET', url: '/customers/{customerId}/documents/{documentId}', display: 'Get document', params: [ 'customerId', 'documentId' ] }
      { name: 'document-versions', method: 'GET', url: '/customers/{customerId}/documents/{documentId}/versions', display: 'Get document versions', params: [ 'customerId', 'documentId' ] }
      { name: 'document-text', method: 'GET', url: '/customers/{customerId}/documents/{documentId}/text', display: 'Get document text', params: [ 'customerId', 'documentId' ] }
      { name: 'workspaces-recent', method: 'GET', url: '/customers/{customerId}/workspaces', display: 'Recent workspaces', params: [ 'customerId' ] }
      { name: 'workspace-children', method: 'GET', url: '/customers/{customerId}/workspaces/{workspaceId}/children', display: 'Workspace children', params: [ 'customerId', 'workspaceId' ] }
      { name: 'folders-search', method: 'GET', url: '/customers/{customerId}/folders/search', display: 'Search folders', params: [ 'customerId' ] }
      { name: 'folder-children', method: 'GET', url: '/customers/{customerId}/folders/{folderId}/children', display: 'Folder children', params: [ 'customerId', 'folderId' ] }
      { name: 'clients-search', method: 'GET', url: '/customers/{customerId}/clients/search', display: 'Search clients', params: [ 'customerId' ] }
      { name: 'users-search', method: 'GET', url: '/customers/{customerId}/users/search', display: 'Search users', params: [ 'customerId' ] }
      { name: 'users-me', method: 'GET', url: '/customers/{customerId}/users/me', display: 'Current user', params: [ 'customerId' ] }
    ]
    policyXml: loadTextContent('../../docs/apim/policies/imanage-work-mcp.xml')
  }
  dependsOn: [
    subscriptionKeyNv
  ]
}

@description('Public MCP route URL the hosted agent uses as its MCP tool.')
output mcpRouteUrl string = '${apim.properties.gatewayUrl}/imanage/mcp'

@description('Public Work route URL the web proxy calls for Work REST.')
output workRouteUrl string = '${apim.properties.gatewayUrl}/imanage/work'