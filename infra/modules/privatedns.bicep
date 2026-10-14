// Private DNS zones for every private-endpoint service, linked to the VNet.
// One zone per service; VNet links enable in-VNet name resolution to private IPs.

@description('Tags.')
param tags object = {}

@description('Resource id of the VNet to link the zones to.')
param vnetId string

@description('Environment name (used to name the VNet links).')
param environmentName string

@description('Private DNS zone names to create + link.')
param zoneNames array = [
  'privatelink.azure-api.net'
  'privatelink.azurewebsites.net'
  'privatelink.vaultcore.azure.net'
  'privatelink.blob.core.windows.net'
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.search.windows.net'
  'privatelink.documents.azure.com'
]

resource zones 'Microsoft.Network/privateDnsZones@2020-06-01' = [
  for name in zoneNames: {
    name: name
    location: 'global'
    tags: tags
  }
]

resource links 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = [
  for (name, i) in zoneNames: {
    parent: zones[i]
    name: '${environmentName}-link'
    location: 'global'
    tags: tags
    properties: {
      registrationEnabled: false
      virtualNetwork: {
        id: vnetId
      }
    }
  }
]

@description('Map of zone name -> zone resource id.')
output zoneIds object = toObject(zoneNames, name => name, name => resourceId('Microsoft.Network/privateDnsZones', name))
