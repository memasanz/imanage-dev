// =============================================================================
// App Service — Linux Python host for the rebuilt FastAPI proxy + SPA.
//
// Private by design: public network access disabled, inbound private endpoint,
// outbound regional VNet integration (all upstream calls leave via APIM).
// =============================================================================

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('App Service name.')
param appServiceName string

@description('App Service Plan name.')
param planName string

@description('Plan SKU (default P1v3).')
param skuName string = 'P1v3'

@description('User-assigned identity resource id for the app.')
param userAssignedIdentityId string

@description('User-assigned identity client id (for Key Vault references / AAD).')
param userAssignedIdentityClientId string

@description('Subnet id for regional VNet integration (outbound).')
param vnetIntegrationSubnetId string

@description('Subnet id for the inbound private endpoint.')
param privateEndpointSubnetId string

@description('Private DNS zone id for privatelink.azurewebsites.net.')
param privateDnsZoneId string

@description('Application Insights connection string.')
param appInsightsConnectionString string

@description('Extra application settings (name/value) merged into the site config.')
param extraAppSettings array = []

@description('Startup command.')
param startupCommand string = 'python -m uvicorn app.main:app --host 0.0.0.0 --port 8000'

@description('Health check probe path (backend serves /api/health; mock upstream serves /health).')
param healthCheckPath string = '/api/health'

@description('azd service name tag (maps this site to a service in azure.yaml).')
param azdServiceName string = 'web'

@description('Allow public network access (open-network stamp; the real web app is always Disabled).')
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Disabled'

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
    publicNetworkAccess: publicNetworkAccess
    virtualNetworkSubnetId: vnetIntegrationSubnetId
    keyVaultReferenceIdentity: userAssignedIdentityId
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      alwaysOn: true
      ftpsState: 'Disabled'
      vnetRouteAllEnabled: true
      healthCheckPath: healthCheckPath
      minTlsVersion: '1.2'
      http20Enabled: true
      appCommandLine: startupCommand
      appSettings: concat(baseAppSettings, extraAppSettings)
    }
  }
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${appServiceName}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${appServiceName}'
        properties: {
          privateLinkServiceId: site.id
          groupIds: [
            'sites'
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
        name: 'sites'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

@description('App Service resource id.')
output siteId string = site.id

@description('App Service default hostname.')
output defaultHostName string = site.properties.defaultHostName

@description('App Service system-assigned-free principal (user-assigned used instead).')
output siteName string = site.name
