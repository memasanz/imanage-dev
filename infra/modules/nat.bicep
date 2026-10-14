// NAT Gateway — deterministic egress for APIM → iManage SaaS (stable outbound IP for
// customer allow-listing). Created in managed mode; associated to snet-nat by network.bicep.

@description('Region.')
param location string

@description('Tags.')
param tags object = {}

@description('NAT Gateway name.')
param natGatewayName string

@description('Public IP name.')
param publicIpName string

@description('Availability zones for the public IP (zone-redundant by default).')
param zones array = [
  '1'
  '2'
  '3'
]

resource pip 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: publicIpName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  zones: zones
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource natGateway 'Microsoft.Network/natGateways@2024-05-01' = {
  name: natGatewayName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    idleTimeoutInMinutes: 4
    publicIpAddresses: [
      {
        id: pip.id
      }
    ]
  }
}

@description('NAT Gateway resource id (associate to the egress subnet).')
output natGatewayId string = natGateway.id

@description('Outbound public IP to share with iManage for allow-listing.')
output outboundIpId string = pip.id
