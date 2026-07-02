//https://github.com/microsoft-foundry/foundry-samples/blob/main/infrastructure/infrastructure-setup-bicep/00-basic/main.bicep

param coursePrefix string
param aiFoundryName string = coursePrefix
param aiProjectName string = '${aiFoundryName}-proj'
param contentSafetyName string = '${coursePrefix}-csafety'
param redisName string = '${coursePrefix}-redis'
param location string = resourceGroup().location
param llmModelDeploymentName string = '${coursePrefix}-llm-deploy'

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

// https://ai.azure.com/catalog/models/gpt-4.1-mini
resource llmModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01'= {
  parent: aiFoundry
  name: llmModelDeploymentName
  sku : {
    capacity: 1
    name: 'GlobalStandard'
  }
  properties: {
    model:{
      name: 'gpt-4.1-mini'
      format: 'OpenAI'
      version: '2025-04-14'
    }
  }
}

/*
  Content Safety service to moderate text, images, and other content
*/
resource contentSafety 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: contentSafetyName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'ContentSafety'
  properties: {
    customSubDomainName: contentSafetyName
    disableLocalAuth: false
  }
}

/*
  Azure Managed Redis for session memory and conversation persistence
*/
resource redisEnterprise 'Microsoft.Cache/redisEnterprise@2024-09-01-preview' = {
  name: redisName
  location: location
  properties: {
    minimumTlsVersion: '1.2'
  }
  sku: {
    name: 'Balanced_B5'
  }
  tags: {
    environment: 'development'
    purpose: 'session-memory-for-ai-agent'
  }
}

// Database is required for Azure Managed Redis to function
resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2024-09-01-preview' = {
  name: 'default'
  parent: redisEnterprise
  properties: {
    accessKeysAuthentication: 'Enabled'
    clientProtocol: 'Encrypted'
    port: 10000
    evictionPolicy: 'NoEviction'
    clusteringPolicy: 'EnterpriseCluster'
  }
}

output OPENAI_ENDPOINT string = 'https://${aiFoundry.properties.customSubDomainName}.services.ai.azure.com/openai/v1'
output LLM_MODEL_DEPLOYMENT_NAME string = llmModelDeployment.name
output CONTENT_SAFETY_ENDPOINT string = 'https://${contentSafety.properties.customSubDomainName}.cognitiveservices.azure.com/'
output REDIS_HOSTNAME string = redisEnterprise.properties.hostName
output REDIS_PORT int = 10000
output REDIS_ACCESS_KEY string = redisDatabase.listKeys().primaryKey
