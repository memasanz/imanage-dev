// =============================================================================
// Networking module — managed or bring-your-own VNet.
//
// byoVnet = false : create the VNet, 6 role subnets, and NSGs.
// byoVnet = true  : reference an existing VNet; map caller-supplied subnet ids.
//
// Subnet roles (keys in subnetPrefixes / existingSubnetResourceIds):
//   apim             -> APIM Std v2 outbound    (delegation Microsoft.Web/serverFarms)
//   appservice       -> App Service outbound    (delegation Microsoft.Web/serverFarms)
//   agents           -> Foundry agent injection (delegation Microsoft.App/environments)
//   privateendpoints -> private endpoints       (PE network policies disabled)
//   mcp              -> internal Container Apps env for the MCP gateway (delegation Microsoft.App/environments)
//   nat              -> NAT Gateway association
// =============================================================================

@description('Region for created network resources.')
param location string

@description('Tags applied to created resources.')
param tags object = {}

@description('Environment name (used for NSG names).')
param environmentName string

@description('Name of the VNet to create (managed mode only).')
param vnetName string

@description('false = create VNet/subnets/NSGs. true = consume an existing VNet.')
param byoVnet bool

@description('[managed] VNet address space.')
param vnetAddressPrefix string

@description('[managed] Subnet prefixes keyed by role.')
param subnetPrefixes object

@description('[BYO] Existing VNet resource id.')
param existingVnetResourceId string

@description('[BYO] Existing subnet resource ids keyed by role.')
param existingSubnetResourceIds object

@description('NSG name prefix (abbreviation).')
param nsgNamePrefix string

@description('[managed] NAT Gateway resource id to associate with snet-nat (empty = none).')
param natGatewayId string = ''

// --- Managed mode: NSGs for the delegated/PE subnets -----------------------
// Rules are intentionally minimal here (default deny-inbound-from-internet applies via
// platform defaults). Epic 3 (Networking) tightens these per-subnet.
var nsgRoles = [
  'apim'
  'appservice'
  'agents'
  'privateendpoints'
  'mcp'
]

resource nsgs 'Microsoft.Network/networkSecurityGroups@2024-05-01' = [
  for role in nsgRoles: if (!byoVnet) {
    name: '${nsgNamePrefix}${environmentName}-${role}'
    location: location
    tags: tags
    properties: {
      securityRules: []
    }
  }
]

// --- Managed mode: the VNet with all six role subnets ----------------------
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = if (!byoVnet) {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: 'snet-apim'
        properties: {
          addressPrefix: subnetPrefixes.apim
          networkSecurityGroup: { id: nsgs[0].id }
          delegations: [
            {
              name: 'apim-serverfarms'
              properties: { serviceName: 'Microsoft.Web/serverFarms' }
            }
          ]
        }
      }
      {
        name: 'snet-appservice'
        properties: {
          addressPrefix: subnetPrefixes.appservice
          networkSecurityGroup: { id: nsgs[1].id }
          delegations: [
            {
              name: 'appservice-serverfarms'
              properties: { serviceName: 'Microsoft.Web/serverFarms' }
            }
          ]
        }
      }
      {
        name: 'snet-agents'
        properties: {
          addressPrefix: subnetPrefixes.agents
          networkSecurityGroup: { id: nsgs[2].id }
          delegations: [
            {
              name: 'agents-app-environments'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
        }
      }
      {
        name: 'snet-privateendpoints'
        properties: {
          addressPrefix: subnetPrefixes.privateendpoints
          networkSecurityGroup: { id: nsgs[3].id }
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'snet-mcp'
        properties: {
          addressPrefix: subnetPrefixes.mcp
          networkSecurityGroup: { id: nsgs[4].id }
          delegations: [
            {
              name: 'mcp-app-environments'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
        }
      }
      {
        name: 'snet-nat'
        properties: {
          addressPrefix: subnetPrefixes.nat
          natGateway: empty(natGatewayId) ? null : {
            id: natGatewayId
          }
        }
      }
    ]
  }
}

// --- Resolved outputs (uniform across both modes) --------------------------
var managedVnetId = byoVnet ? '' : vnet.id
var managedSubnetIds = byoVnet ? {} : {
  apim: '${vnet.id}/subnets/snet-apim'
  appservice: '${vnet.id}/subnets/snet-appservice'
  agents: '${vnet.id}/subnets/snet-agents'
  privateendpoints: '${vnet.id}/subnets/snet-privateendpoints'
  mcp: '${vnet.id}/subnets/snet-mcp'
  nat: '${vnet.id}/subnets/snet-nat'
}

@description('Resolved VNet resource id (created or BYO).')
output vnetId string = byoVnet ? existingVnetResourceId : managedVnetId

@description('Resolved subnet resource ids by role (created or BYO).')
output subnetIds object = byoVnet ? existingSubnetResourceIds : managedSubnetIds
