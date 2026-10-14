// =============================================================================
// BYO "standard agent" dependent resources: Cosmos DB (threads), Storage (files),
// AI Search (vector store). All created private (public access disabled, Entra-only).
// Private endpoints are added by private-endpoints.bicep; RBAC by the role modules.
// Mirrors foundry-samples 19-.../standard-dependent-resources.bicep (create-only path).
// =============================================================================

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('Cosmos DB account name.')
param cosmosName string

@description('Storage account name (<=24 chars, lowercase alphanumeric).')
param storageName string

@description('AI Search service name.')
param searchName string

@description('AI Search SKU. basic draws from a separate capacity pool than standard.')
@allowed([
  'basic'
  'standard'
])
param searchSku string = 'basic'

@description('AI Search region. May differ from the stamp region (BYO resources can be cross-region); defaults to the stamp region.')
param searchLocation string = location

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: cosmosName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    isVirtualNetworkFilterEnabled: false
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_GRS'
  }
  properties: {
    accessTier: 'Hot'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    publicNetworkAccess: 'Disabled'
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchName
  location: searchLocation
  tags: tags
  sku: {
    name: searchSku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    disableLocalAuth: false
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    publicNetworkAccess: 'disabled'
    replicaCount: 1
    partitionCount: 1
  }
}

output cosmosName string = cosmos.name
output cosmosId string = cosmos.id
output cosmosDocumentEndpoint string = cosmos.properties.documentEndpoint
output storageName string = storage.name
output storageId string = storage.id
output storageBlobEndpoint string = storage.properties.primaryEndpoints.blob
output searchName string = search.name
output searchId string = search.id
output searchEndpoint string = 'https://${search.name}.search.windows.net'
