// =============================================================================
// Project capability host (kind 'Agents') — binds the BYO Cosmos/Storage/Search
// connections so the injected Agent Service can run. Create AFTER the pre-caphost RBAC
// (Cosmos DB Operator, Storage/Search roles) and the private endpoints exist.
// Verbatim from foundry-samples 19-.../add-project-capability-host.bicep.
// =============================================================================

param cosmosDBConnection string
param azureStorageConnection string
param aiSearchConnection string
param projectName string
param accountName string
param projectCapHost string

var threadConnections = ['${cosmosDBConnection}']
var storageConnections = ['${azureStorageConnection}']
var vectorStoreConnections = ['${aiSearchConnection}']

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  name: projectName
  parent: account
}

resource projectCapabilityHost 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview' = {
  name: projectCapHost
  parent: project
  properties: {
    capabilityHostKind: 'Agents'
    vectorStoreConnections: vectorStoreConnections
    storageConnections: storageConnections
    threadStorageConnections: threadConnections
  }
}

output projectCapHost string = projectCapabilityHost.name
