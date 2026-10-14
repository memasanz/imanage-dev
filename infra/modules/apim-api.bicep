// One iManage/Foundry API on APIM: the API, its fine-grained operations, and its policy.
// Invoked once per API by apim.bicep (avoids unsupported nested for-expressions).

@description('Existing APIM service name.')
param apimName string

@description('API logical name.')
param apiName string

@description('API display name.')
param displayName string

@description('API path prefix.')
param path string

@description('Backend service URL.')
param serviceUrl string

@description('Operations: array of { name, method, url, display }.')
param operations array

@description('Raw XML policy for this API.')
param policyXml string

@description('Require an APIM subscription key on inbound calls. Default false — auth is enforced by the per-API policy (iManage bearer) and managed identity; APIM still logs every call. Set true once per-consumer products/subscriptions are provisioned for quota.')
param subscriptionRequired bool = false

resource apimRef 'Microsoft.ApiManagement/service@2023-05-01-preview' existing = {
  name: apimName
}

resource api 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = {
  parent: apimRef
  name: apiName
  properties: {
    displayName: displayName
    path: path
    serviceUrl: serviceUrl
    protocols: [ 'https' ]
    subscriptionRequired: subscriptionRequired
    subscriptionKeyParameterNames: {
      header: 'Ocp-Apim-Subscription-Key'
      query: 'subscription-key'
    }
  }
}

resource ops 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = [
  for op in operations: {
    parent: api
    name: op.name
    properties: {
      displayName: op.display
      method: op.method
      urlTemplate: op.url
      templateParameters: [
        for p in op.params: {
          name: p
          type: 'string'
          required: true
        }
      ]
    }
  }
]

resource policy 'Microsoft.ApiManagement/service/apis/policies@2023-05-01-preview' = {
  parent: api
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: policyXml
  }
  dependsOn: [
    ops
  ]
}
