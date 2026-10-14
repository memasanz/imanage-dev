// =============================================================================
// Private endpoints for the Foundry account + BYO dependent resources, wired to the
// stamp's EXISTING private DNS zones (passed in — not re-created here, unlike template 19's
// central module, to avoid zone conflicts with privatedns.bicep).
// =============================================================================

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('Subnet id hosting the private endpoints.')
param subnetId string

@description('Foundry account resource id.')
param accountId string

@description('Cosmos DB account resource id.')
param cosmosId string

@description('Storage account resource id.')
param storageId string

@description('AI Search service resource id.')
param searchId string

@description('Private DNS zone ids: { cognitiveservices, openai, servicesai, documents, blob, search }')
param privateDnsZoneIds object

var accountName = last(split(accountId, '/'))
var cosmosName = last(split(cosmosId, '/'))
var storageName = last(split(storageId, '/'))
var searchName = last(split(searchId, '/'))

// --- Foundry account (cognitiveservices + openai + services.ai zones) ------
resource accountPe 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pe-${accountName}'
  location: location
  tags: tags
  properties: {
    subnet: { id: subnetId }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${accountName}'
        properties: {
          privateLinkServiceId: accountId
          groupIds: [ 'account' ]
        }
      }
    ]
  }
}

resource accountPeDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: accountPe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'cognitiveservices', properties: { privateDnsZoneId: privateDnsZoneIds.cognitiveservices } }
      { name: 'openai', properties: { privateDnsZoneId: privateDnsZoneIds.openai } }
      { name: 'servicesai', properties: { privateDnsZoneId: privateDnsZoneIds.servicesai } }
    ]
  }
}

// --- Cosmos DB (Sql group → documents zone) --------------------------------
resource cosmosPe 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pe-${cosmosName}'
  location: location
  tags: tags
  properties: {
    subnet: { id: subnetId }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${cosmosName}'
        properties: {
          privateLinkServiceId: cosmosId
          groupIds: [ 'Sql' ]
        }
      }
    ]
  }
}

resource cosmosPeDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: cosmosPe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'documents', properties: { privateDnsZoneId: privateDnsZoneIds.documents } }
    ]
  }
}

// --- Storage (blob group → blob zone) --------------------------------------
resource storagePe 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pe-${storageName}-blob'
  location: location
  tags: tags
  properties: {
    subnet: { id: subnetId }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${storageName}-blob'
        properties: {
          privateLinkServiceId: storageId
          groupIds: [ 'blob' ]
        }
      }
    ]
  }
}

resource storagePeDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: storagePe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'blob', properties: { privateDnsZoneId: privateDnsZoneIds.blob } }
    ]
  }
}

// --- AI Search (searchService group → search zone) -------------------------
resource searchPe 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pe-${searchName}'
  location: location
  tags: tags
  properties: {
    subnet: { id: subnetId }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${searchName}'
        properties: {
          privateLinkServiceId: searchId
          groupIds: [ 'searchService' ]
        }
      }
    ]
  }
}

resource searchPeDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: searchPe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'search', properties: { privateDnsZoneId: privateDnsZoneIds.search } }
    ]
  }
}
