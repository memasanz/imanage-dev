// =============================================================================
// App Service (public) — Sprint 1 open-network host.
//
// Linux Python site on a dedicated plan. No VNet integration, no private
// endpoint: Sprint 1 deliberately runs on the open network so we can prove the
// hosted-agent <-> APIM path end to end. The private variant (VNet + PE) lives
// in modules/appservice.bicep and is used by the Sprint 2 blueprint.
// =============================================================================

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('App Service name.')
param appServiceName string

@description('App Service Plan name.')
param planName string

@description('Plan SKU.')
param skuName string = 'B1'

@description('User-assigned identity resource id for the app.')
param userAssignedIdentityId string

@description('User-assigned identity client id (for AAD / DefaultAzureCredential).')
param userAssignedIdentityClientId string

@description('Application Insights connection string.')
param appInsightsConnectionString string

@description('Extra application settings (name/value) merged into the site config.')
param extraAppSettings array = []

@description('Startup command.')
param startupCommand string = 'python -m uvicorn app.main:app --host 0.0.0.0 --port 8000'

@description('Health check probe path.')
param healthCheckPath string = '/api/health'

@description('azd service name tag (maps this site to a service in azure.yaml).')
param azdServiceName string = 'web'

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: planName
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

var baseAppSettings = [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsightsConnectionString
  }
  {
    name: 'AZURE_CLIENT_ID'
    value: userAssignedIdentityClientId
  }
  {
    name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
    value: 'true'
  }
  {
    name: 'WEBSITE_RUN_FROM_PACKAGE'
    value: '0'
  }
]

resource site 'Microsoft.Web/sites@2024-04-01' = {
  name: appServiceName
  location: location
  tags: union(tags, { 'azd-service-name': azdServiceName })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    publicNetworkAccess: 'Enabled'
    keyVaultReferenceIdentity: userAssignedIdentityId
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      alwaysOn: true
      ftpsState: 'Disabled'
      healthCheckPath: healthCheckPath
      minTlsVersion: '1.2'
      http20Enabled: true
      appCommandLine: startupCommand
      appSettings: concat(baseAppSettings, extraAppSettings)
    }
  }
}

@description('App Service resource id.')
output siteId string = site.id

@description('App Service default hostname.')
output defaultHostName string = site.properties.defaultHostName

@description('App Service name.')
output siteName string = site.name
