// =============================================================================
// iManage AI Workspace — root orchestrator (subscription scope). SPRINT 1.
//
// Open-network, functionality-first stamp. Creates the resource group and
// deploys only the parts the customer does not bring (web + mock App Services,
// observability, identity) and registers the iManage MCP route onto the BYO
// APIM. Foundry (project + model) and APIM are referenced from .env, not created.
//
// Network isolation (VNet, private endpoints, NAT) is a later sprint.
// =============================================================================

targetScope = 'subscription'

@minLength(2)
@maxLength(20)
@description('Short environment name; used as a prefix for resource names (e.g. azure-imanage-dev).')
param environmentName string

@description('Azure region for the stamp.')
param location string

@description('Resource group to create/use. Defaults to rg-<environmentName>.')
param resourceGroupName string = ''

@description('Tags applied to every resource.')
param tags object = {}

@description('mock = emulated upstream (no live tenant). live = real cloudimanage.com tenant.')
@allowed([ 'mock', 'live' ])
param imanageBackendMode string = 'mock'

// --- BYO Foundry (referenced, not created) ---------------------------------
@description('BYO Foundry project endpoint (https://<account>.services.ai.azure.com/api/projects/<project>).')
param foundryProjectEndpoint string

@description('BYO Foundry model deployment name (e.g. gpt-4o).')
param modelDeploymentName string

// --- BYO APIM (referenced, not created) ------------------------------------
@description('BYO APIM service name.')
param apimServiceName string

@description('Resource group of the BYO APIM.')
param apimResourceGroupName string

@description('BYO APIM gateway URL (https://<apim>.azure-api.net).')
param apimGatewayUrl string

// --- Optional live iManage / secrets ---------------------------------------
@description('[live] iManage MCP base url.')
param imanageMcpUrlLive string = 'https://cloudimanage.com/mcp'

@secure()
@description('iManage subscription key the MCP policy presents to the upstream (secret).')
param imanageSubscriptionKey string = ''

var effectiveResourceGroupName = empty(resourceGroupName) ? 'rg-${environmentName}' : resourceGroupName

var defaultTags = union(tags, {
  'azd-env-name': environmentName
  workload: 'imanage-ai-workspace'
})

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: effectiveResourceGroupName
  location: location
  tags: defaultTags
}

module stamp 'resources.bicep' = {
  scope: rg
  name: 'stamp'
  params: {
    environmentName: environmentName
    location: location
    tags: defaultTags
    imanageBackendMode: imanageBackendMode
    foundryProjectEndpoint: foundryProjectEndpoint
    modelDeploymentName: modelDeploymentName
    apimServiceName: apimServiceName
    apimResourceGroupName: apimResourceGroupName
    apimGatewayUrl: apimGatewayUrl
    imanageMcpUrlLive: imanageMcpUrlLive
    imanageSubscriptionKey: imanageSubscriptionKey
  }
}

@description('Resource group the stamp was deployed into.')
output AZURE_RESOURCE_GROUP string = rg.name

@description('Active iManage backend mode.')
output IMANAGE_BACKEND_MODE string = imanageBackendMode

@description('Web app URL.')
output WEB_APP_URI string = stamp.outputs.webAppUri

@description('Mock upstream URL (empty in live mode).')
output MOCK_UPSTREAM_URI string = stamp.outputs.mockUpstreamUri

@description('Public iManage MCP route (hosted-agent MCP tool).')
output IMANAGE_MCP_URL string = stamp.outputs.mcpRouteUrl
