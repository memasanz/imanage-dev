// Observability — Log Analytics workspace + Application Insights (workspace-based).
// APIM and Foundry diagnostics route here in later epics.

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('Log Analytics workspace name.')
param logAnalyticsName string

@description('Application Insights name.')
param applicationInsightsName string

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

@description('Log Analytics workspace resource id.')
output logAnalyticsWorkspaceId string = logAnalytics.id

@description('Application Insights resource id.')
output appInsightsId string = appInsights.id

@description('Application Insights connection string.')
output appInsightsConnectionString string = appInsights.properties.ConnectionString
