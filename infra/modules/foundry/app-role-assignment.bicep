// Cognitive Services User → the web app's managed identity, so the App Service agent
// bridge can call the model/project data plane through the account.

@description('Foundry account name.')
param accountName string

@description('App (web) managed-identity principal id.')
param appPrincipalId string

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: accountName
}

// Cognitive Services User
resource cognitiveServicesUser 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  scope: resourceGroup()
}

resource appModelRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(appPrincipalId, cognitiveServicesUser.id, account.id)
  properties: {
    principalId: appPrincipalId
    roleDefinitionId: cognitiveServicesUser.id
    principalType: 'ServicePrincipal'
  }
}
