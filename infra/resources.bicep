// =============================================================================
// iManage AI Workspace — stamp (resource-group scope). SPRINT 1 (open network).
//
// Deploys only what the customer does NOT bring:
//   - Observability (Log Analytics + App Insights)
//   - A user-assigned identity for the web app
//   - The web App Service (rebuilt proxy + SPA)
//   - The mock upstream App Service (mock mode only)
//   - The iManage Work + MCP routes + policy registered onto the BYO APIM
//
// Customer-provided (BYO via .env), referenced not created:
//   - Azure AI Foundry project + model deployment (models/agents already route
//     through the BYO APIM)
//   - Customer-provided API Management instance
//
// Sprint 1 is deliberately open-network: no VNet, private endpoints or NAT.
// Network isolation is a later sprint.
// =============================================================================

@description('Short environment name; used as a resource-name prefix.')
param environmentName string

@description('Azure region for the stamp.')
param location string

@description('Tags applied to every resource.')
param tags object = {}

@description('mock = emulated upstream (no live tenant). live = real cloudimanage.com tenant.')
@allowed([ 'mock', 'live' ])
param imanageBackendMode string

// --- BYO Foundry -----------------------------------------------------------
@description('BYO Foundry project endpoint (https://<account>.services.ai.azure.com/api/projects/<project>).')
param foundryProjectEndpoint string

@description('BYO Foundry model deployment name (e.g. gpt-4o).')
param modelDeploymentName string

// --- BYO APIM --------------------------------------------------------------
@description('BYO APIM service name.')
param apimServiceName string

@description('Resource group of the BYO APIM (may differ from the stamp RG).')
param apimResourceGroupName string

@description('BYO APIM gateway URL (https://<apim>.azure-api.net).')
param apimGatewayUrl string

// --- live iManage (used when imanageBackendMode = live) --------------------
@description('[live] iManage MCP base url.')
param imanageMcpUrlLive string = 'https://cloudimanage.com/mcp'

@description('[live] iManage Work REST base url.')
param imanageWorkUrlLive string = 'https://cloudimanage.com/work/api/v2'

@secure()
@description('iManage subscription key the MCP policy presents to the upstream (secret).')
param imanageSubscriptionKey string = ''

var abbrs = loadJsonContent('abbreviations.json')
var mockExperience = loadJsonContent('../config/mock-experience.json')
var resourceToken = uniqueString(subscription().id, resourceGroup().id, environmentName)
var isMock = imanageBackendMode == 'mock'

// --- Predictable names -----------------------------------------------------
var webAppName = take('${abbrs.appService}${environmentName}-web-${resourceToken}', 60)
var mockAppName = take('${abbrs.appService}${environmentName}-mock-${resourceToken}', 60)
var spaOrigin = 'https://${webAppName}.azurewebsites.net'

// Backend URL the APIM /imanage/mcp route points at.
var imanageMcpUrl = isMock ? 'https://${mockAppName}.azurewebsites.net/mcp' : imanageMcpUrlLive

// Backend URL the APIM /imanage/work route points at (serviceUrl; operations append
// /customers/{id}/...). The web proxy's Work REST calls flow through this route.
var imanageWorkUrl = isMock ? 'https://${mockAppName}.azurewebsites.net/work/api/v2' : imanageWorkUrlLive

// Public MCP route the hosted agent uses as its MCP tool.
var mcpRouteUrl = '${apimGatewayUrl}/imanage/mcp'

// --- Observability ---------------------------------------------------------
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    logAnalyticsName: '${abbrs.logAnalyticsWorkspace}${environmentName}'
    applicationInsightsName: '${abbrs.applicationInsights}${environmentName}'
  }
}

// --- Identity --------------------------------------------------------------
module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    location: location
    tags: tags
    namePrefix: abbrs.managedIdentityUserAssigned
    environmentName: environmentName
  }
}

// --- Mock upstream (mock mode only) ----------------------------------------
module mockUpstream 'modules/webapp-public.bicep' = if (isMock) {
  name: 'mock-upstream'
  params: {
    location: location
    tags: tags
    appServiceName: mockAppName
    planName: '${abbrs.appServicePlan}${environmentName}-mock'
    skuName: 'B1'
    azdServiceName: 'mock'
    healthCheckPath: '/health'
    userAssignedIdentityId: identity.outputs.appIdentityId
    userAssignedIdentityClientId: identity.outputs.appIdentityClientId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

// --- Web app (rebuilt proxy + SPA) -----------------------------------------
module web 'modules/webapp-public.bicep' = {
  name: 'web'
  params: {
    location: location
    tags: tags
    appServiceName: webAppName
    planName: '${abbrs.appServicePlan}${environmentName}-web'
    skuName: 'B1'
    azdServiceName: 'web'
    healthCheckPath: '/api/health'
    userAssignedIdentityId: identity.outputs.appIdentityId
    userAssignedIdentityClientId: identity.outputs.appIdentityClientId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    extraAppSettings: concat([
      { name: 'IMANAGE_BACKEND_MODE', value: imanageBackendMode }
      { name: 'APIM_BASE_URL', value: apimGatewayUrl }
      { name: 'IMANAGE_MCP_URL', value: mcpRouteUrl }
      { name: 'FOUNDRY_PROJECT_ENDPOINT', value: foundryProjectEndpoint }
      { name: 'MODEL_DEPLOYMENT_NAME', value: modelDeploymentName }
      { name: 'IMANAGE_CUSTOMER_ID', value: mockExperience.imanageCustomerId }
      { name: 'IMANAGE_LIBRARIES', value: join(mockExperience.imanageLibraries, ',') }
      { name: 'IMANAGE_FIELD_MAP', value: string(mockExperience.fieldMap) }
    ], isMock ? [
      { name: 'MOCK_UPSTREAM_URL', value: 'https://${mockAppName}.azurewebsites.net' }
    ] : [])
  }
}

// --- Register the iManage MCP route/policy onto the BYO APIM ----------------
module apimConfig 'modules/apim-config.bicep' = {
  name: 'apim-config'
  scope: resourceGroup(apimResourceGroupName)
  params: {
    apimName: apimServiceName
    imanageMcpUrl: imanageMcpUrl
    imanageWorkUrl: imanageWorkUrl
    imanageSubscriptionKey: imanageSubscriptionKey
  }
  dependsOn: [
    mockUpstream
  ]
}

// --- Outputs ---------------------------------------------------------------
output resourceToken string = resourceToken
output imanageBackendMode string = imanageBackendMode
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
output appIdentityClientId string = identity.outputs.appIdentityClientId
output appIdentityPrincipalId string = identity.outputs.appIdentityPrincipalId
output apimGatewayUrl string = apimGatewayUrl
output apimServiceName string = apimServiceName
output mcpRouteUrl string = mcpRouteUrl
output foundryProjectEndpoint string = foundryProjectEndpoint
output modelDeploymentName string = modelDeploymentName
output webAppName string = webAppName
output webAppUri string = spaOrigin
output mockUpstreamName string = isMock ? mockAppName : ''
output mockUpstreamUri string = isMock ? 'https://${mockAppName}.azurewebsites.net' : ''
