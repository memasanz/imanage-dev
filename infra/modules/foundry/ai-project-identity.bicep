// =============================================================================
// Foundry project + the three BYO connections the capability host binds (CosmosDB,
// AzureStorageAccount, CognitiveSearch), all Entra (AAD) auth.
// Mirrors foundry-samples 19-.../ai-project-identity.bicep (same-RG variant).
// =============================================================================

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('Parent Foundry account name.')
param accountName string

@description('Project name.')
param projectName string

@description('Project display description.')
param projectDescription string = 'iManage AI Workspace agent project'

@description('Cosmos DB account name.')
param cosmosName string

@description('Storage account name.')
param storageName string

@description('AI Search service name.')
param searchName string

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: accountName
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = {
  name: cosmosName
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageName
}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectName
    description: projectDescription
  }

  resource cosmosConnection 'connections@2025-04-01-preview' = {
    name: '${projectName}-cosmos'
    properties: {
      category: 'CosmosDB'
      target: cosmos.properties.documentEndpoint
      authType: 'AAD'
      isSharedToAll: true
      metadata: {
        ApiType: 'Azure'
        ResourceId: cosmos.id
        location: cosmos.location
      }
    }
  }

  resource storageConnection 'connections@2025-04-01-preview' = {
    name: '${projectName}-storage'
    properties: {
      category: 'AzureStorageAccount'
      target: storage.properties.primaryEndpoints.blob
      authType: 'AAD'
      isSharedToAll: true
      metadata: {
        ApiType: 'Azure'
        ResourceId: storage.id
        location: storage.location
      }
    }
  }

  resource searchConnection 'connections@2025-04-01-preview' = {
    name: '${projectName}-search'
    properties: {
      category: 'CognitiveSearch'
      target: 'https://${search.name}.search.windows.net'
      authType: 'AAD'
      isSharedToAll: true
      metadata: {
        ApiType: 'Azure'
        ResourceId: search.id
        location: search.location
      }
    }
  }
}

#disable-next-line BCP053
output projectWorkspaceId string = project.properties.internalId
output projectPrincipalId string = project.identity.principalId
output projectName string = project.name
output cosmosConnectionName string = project::cosmosConnection.name
output storageConnectionName string = project::storageConnection.name
output searchConnectionName string = project::searchConnection.name
