// User-assigned managed identities for the stamp.
//   app   -> App Service (Key Vault read, calls APIM)
//   apim  -> API Management (Key Vault named values, auth to Foundry model)
// Foundry's project identity is system-assigned and handled in the Foundry module.

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('Prefix for identity names (abbreviation).')
param namePrefix string

@description('Environment name.')
param environmentName string

resource appIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}${environmentName}-app'
  location: location
  tags: tags
}

resource apimIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}${environmentName}-apim'
  location: location
  tags: tags
}

@description('App Service UAMI resource id.')
output appIdentityId string = appIdentity.id

@description('App Service UAMI principal id.')
output appIdentityPrincipalId string = appIdentity.properties.principalId

@description('App Service UAMI client id.')
output appIdentityClientId string = appIdentity.properties.clientId

@description('APIM UAMI resource id.')
output apimIdentityId string = apimIdentity.id

@description('APIM UAMI principal id.')
output apimIdentityPrincipalId string = apimIdentity.properties.principalId
