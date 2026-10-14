// =============================================================================
// Foundry account + model deployment, with AGENT VNET INJECTION.
//
// networkInjections scenario 'agent' routes the Agent Service DataProxy egress into
// `agentSubnetId` (snet-agents). It is set HERE, at account creation, and CANNOT be added
// later — an account made without it must be recreated. Public access disabled, Entra-only.
// Mirrors foundry-samples 19-private-network-agent-tools/.../ai-account-identity.bicep.
// =============================================================================

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('Foundry (AI Services) account name.')
param accountName string

@description('Subnet id for agent VNet injection (delegated to Microsoft.App/environments).')
param agentSubnetId string

@description('Model deployment name (swappable).')
param deploymentName string

@description('Model name.')
param modelName string

@description('Model version.')
param modelVersion string

@description('Deployment capacity (TPM in thousands).')
param deploymentCapacity int

#disable-next-line BCP036
resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    publicNetworkAccess: 'Disabled'
    disableLocalAuth: true
    networkAcls: {
      defaultAction: 'Deny'
      virtualNetworkRules: []
      ipRules: []
      bypass: 'AzureServices'
    }
    // Agent VNet injection — immutable; set at creation only.
    networkInjections: [
      {
        scenario: 'agent'
        subnetArmId: agentSubnetId
        useMicrosoftManagedNetwork: false
      }
    ]
  }
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: account
  name: deploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: deploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
  }
}

output accountName string = account.name
output accountId string = account.id
output endpoint string = account.properties.endpoint
output accountPrincipalId string = account.identity.principalId
output deploymentName string = deployment.name
