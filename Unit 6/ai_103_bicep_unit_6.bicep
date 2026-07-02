param coursePrefix string
param aiSearchName string = '${coursePrefix}-aisearch'
param location string = resourceGroup().location

// Azure AI Search resource
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: aiSearchName
  location: location
  sku: {
    name: 'standard'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    disableLocalAuth: true
  }
}

// Output the search service endpoint
output searchServiceEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchServiceName string = searchService.name
