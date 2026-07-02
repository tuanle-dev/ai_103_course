//https://github.com/microsoft-foundry/foundry-samples/blob/main/infrastructure/infrastructure-setup-bicep/00-basic/main.bicep

param coursePrefix string
param aiFoundryName string = coursePrefix
param aiProjectName string = '${aiFoundryName}-proj'
param aiSearchName string = '${coursePrefix}-aisearch'
param location string = resourceGroup().location
param embeddingModelDeploymentName string = '${coursePrefix}-embedding-deploy'

/*
  An AI Foundry resources is a variant of a CognitiveServices/account resource type
*/ 
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: aiFoundryName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    // required to work in AI Foundry
    allowProjectManagement: true

    // Defines developer API endpoint subdomain
    customSubDomainName: aiFoundryName

    disableLocalAuth: false
  }
}

/*
  Developer APIs are exposed via a project, which groups in- and outputs that relate to one use case, including files.
  Its advisable to create one project right away, so development teams can directly get started.
  Projects may be granted individual RBAC permissions and identities on top of what account provides.
*/
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  name: aiProjectName
  parent: aiFoundry
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

/*
  Deploying models to use in playground, agents and other tools.
*/

// https://ai.azure.com/catalog/models/text-embedding-3-small
resource embeddingModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01'= {
  parent: aiFoundry
  name: embeddingModelDeploymentName
  sku : {
    capacity: 1
    name: 'GlobalStandard'
  }
  properties: {
    model:{
      name: 'text-embedding-3-small' // 1536 dimensions, good for semantic search and embedding use cases
      format: 'OpenAI'
      version: '1'
    }
  }
}

/*
  Azure AI Search resource
*/
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

output OPENAI_ENDPOINT string = 'https://${aiFoundry.properties.customSubDomainName}.services.ai.azure.com/openai/v1'
output EMBEDDING_MODEL_DEPLOYMENT_NAME string = embeddingModelDeployment.name
output AI_SEARCH_SERVICE_ENDPOINT string = 'https://${searchService.name}.search.windows.net'
output AI_SEARCH_SERVICE_DEPLOYMENT_NAME string = searchService.name
