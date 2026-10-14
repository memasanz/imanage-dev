// =============================================================================
// Azure AI Foundry — PRIVATE "standard agent" setup with AGENT VNET INJECTION.
//
// This is a thin orchestrator that mirrors the module structure of foundry-samples
// template 19 (19-private-network-agent-tools). Each concern lives in modules/foundry/:
//
//   ai-account-identity          account + networkInjections 'agent' + model deployment
//   standard-dependent-resources BYO Cosmos / Storage / AI Search (all private)
//   private-endpoints            PEs for account + BYO resources (reuse stamp DNS zones)
//   ai-project-identity          project + Cosmos/Storage/Search connections
//   format-project-workspace-id  internalId -> GUID (scopes container RBAC)
//   *-role-assignment(s)         RBAC, ordered around the capability host
//   add-project-capability-host  capabilityHost kind 'Agents' (binds the connections)
//
// RBAC ordering is load-bearing:
//   BEFORE caphost: Cosmos DB Operator, Storage Blob Data Contributor, Search roles
//   AFTER  caphost: Storage Blob Data Owner + Cosmos data-plane contributor (container-scoped)
//
// Agent injection is immutable at account creation — a bare account cannot be upgraded;
// it must be deleted and recreated through this module.
// =============================================================================

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('Foundry (AI Services) account name.')
param accountName string

@description('Project name.')
param projectName string = 'imanage'

@description('Capability host name (project scope).')
param projectCapHost string = 'caphostproj'

@description('Model deployment name (swappable).')
param deploymentName string = 'gpt-4o'

@description('Model name.')
param modelName string = 'gpt-4o'

@description('Model version.')
param modelVersion string = '2024-11-20'

@description('Deployment capacity (TPM in thousands).')
param deploymentCapacity int = 20

@description('Cosmos DB account name (threads store).')
param cosmosName string

@description('Storage account name (file store, <=24 chars lowercase alphanumeric).')
param storageName string

@description('AI Search service name (vector store).')
param searchName string

@description('AI Search region (BYO resources may be cross-region); defaults to the stamp region.')
param searchLocation string = location

@description('Subnet id for inbound private endpoints.')
param privateEndpointSubnetId string

@description('Subnet id (snet-agents) for Agent Service VNet injection.')
param agentSubnetId string

@description('Private DNS zone ids: { cognitiveservices, openai, servicesai, documents, blob, search }.')
param privateDnsZoneIds object

@description('App (web) managed-identity principal id — granted Cognitive Services User.')
param appPrincipalId string = ''

// --- 1. Account (+ injection) + model deployment ---------------------------
module account 'foundry/ai-account-identity.bicep' = {
  name: 'foundry-account'
  params: {
    location: location
    tags: tags
    accountName: accountName
    agentSubnetId: agentSubnetId
    deploymentName: deploymentName
    modelName: modelName
    modelVersion: modelVersion
    deploymentCapacity: deploymentCapacity
  }
}

// --- 2. BYO dependent resources --------------------------------------------
module dependent 'foundry/standard-dependent-resources.bicep' = {
  name: 'foundry-dependent'
  params: {
    location: location
    tags: tags
    cosmosName: cosmosName
    storageName: storageName
    searchName: searchName
    searchLocation: searchLocation
  }
}

// --- 3. Private endpoints (account + BYO), reusing stamp DNS zones ----------
module privateEndpoints 'foundry/private-endpoints.bicep' = {
  name: 'foundry-private-endpoints'
  params: {
    location: location
    tags: tags
    subnetId: privateEndpointSubnetId
    accountId: account.outputs.accountId
    cosmosId: dependent.outputs.cosmosId
    storageId: dependent.outputs.storageId
    searchId: dependent.outputs.searchId
    privateDnsZoneIds: privateDnsZoneIds
  }
}

// --- 4. Project + connections ----------------------------------------------
module project 'foundry/ai-project-identity.bicep' = {
  name: 'foundry-project'
  params: {
    location: location
    tags: tags
    accountName: account.outputs.accountName
    projectName: projectName
    cosmosName: dependent.outputs.cosmosName
    storageName: dependent.outputs.storageName
    searchName: dependent.outputs.searchName
  }
}

module workspaceId 'foundry/format-project-workspace-id.bicep' = {
  name: 'foundry-workspace-id'
  params: {
    projectWorkspaceId: project.outputs.projectWorkspaceId
  }
}

// --- 5. Pre-caphost RBAC (project MI -> dependent resources) ---------------
module cosmosAccountRole 'foundry/cosmosdb-account-role-assignment.bicep' = {
  name: 'foundry-rbac-cosmos-operator'
  params: {
    cosmosDBName: dependent.outputs.cosmosName
    projectPrincipalId: project.outputs.projectPrincipalId
  }
}

module storageAccountRole 'foundry/azure-storage-account-role-assignment.bicep' = {
  name: 'foundry-rbac-storage-contributor'
  params: {
    azureStorageName: dependent.outputs.storageName
    projectPrincipalId: project.outputs.projectPrincipalId
  }
}

module searchRoles 'foundry/ai-search-role-assignments.bicep' = {
  name: 'foundry-rbac-search'
  params: {
    aiSearchName: dependent.outputs.searchName
    projectPrincipalId: project.outputs.projectPrincipalId
  }
}

// --- 6. Capability host (after pre-caphost RBAC + private endpoints) --------
module capabilityHost 'foundry/add-project-capability-host.bicep' = {
  name: 'foundry-caphost'
  params: {
    accountName: account.outputs.accountName
    projectName: project.outputs.projectName
    projectCapHost: projectCapHost
    cosmosDBConnection: project.outputs.cosmosConnectionName
    azureStorageConnection: project.outputs.storageConnectionName
    aiSearchConnection: project.outputs.searchConnectionName
  }
  dependsOn: [
    cosmosAccountRole
    storageAccountRole
    searchRoles
    privateEndpoints
  ]
}

// --- 7. Post-caphost container-scoped RBAC ---------------------------------
module storageContainerRole 'foundry/blob-storage-container-role-assignments.bicep' = {
  name: 'foundry-rbac-storage-owner'
  params: {
    storageName: dependent.outputs.storageName
    aiProjectPrincipalId: project.outputs.projectPrincipalId
    workspaceId: workspaceId.outputs.projectWorkspaceIdGuid
  }
  dependsOn: [
    capabilityHost
    storageAccountRole
  ]
}

module cosmosContainerRole 'foundry/cosmos-container-role-assignments.bicep' = {
  name: 'foundry-rbac-cosmos-data'
  params: {
    cosmosAccountName: dependent.outputs.cosmosName
    projectPrincipalId: project.outputs.projectPrincipalId
    projectWorkspaceId: workspaceId.outputs.projectWorkspaceIdGuid
  }
  dependsOn: [
    capabilityHost
    storageContainerRole
  ]
}

// --- 8. App identity -> model (Cognitive Services User) --------------------
module appRole 'foundry/app-role-assignment.bicep' = if (!empty(appPrincipalId)) {
  name: 'foundry-rbac-app-model'
  params: {
    accountName: account.outputs.accountName
    appPrincipalId: appPrincipalId
  }
}

// --- Outputs ---------------------------------------------------------------
@description('Foundry account resource id.')
output accountId string = account.outputs.accountId

@description('Foundry account endpoint.')
output endpoint string = account.outputs.endpoint

@description('Foundry project endpoint (for AIProjectClient / agent invocation).')
output projectEndpoint string = 'https://${accountName}.services.ai.azure.com/api/projects/${projectName}'

@description('Model deployment name.')
output deploymentName string = account.outputs.deploymentName

@description('Account system-assigned principal id.')
output accountPrincipalId string = account.outputs.accountPrincipalId

@description('Project system-assigned principal id.')
output projectPrincipalId string = project.outputs.projectPrincipalId
