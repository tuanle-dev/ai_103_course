//https://github.com/microsoft-foundry/foundry-samples/blob/main/infrastructure/infrastructure-setup-bicep/00-basic/main.bicep

param coursePrefix string
param aiFoundryName string = coursePrefix
param aiProjectName string = '${aiFoundryName}-proj'
param contentSafetyName string = '${coursePrefix}-csafety'
param languageName string = '${coursePrefix}-language'
param keyVaultName string = '${coursePrefix}-kvault'
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
  Azure AI Language service for Natural Language Processing (NLP)
  Provides: Language detection, PII redaction, NER, key phrase extraction, sentiment analysis
*/
resource language 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: languageName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'F0' // Free tier, change to 'S0' for production use
  }
  kind: 'TextAnalytics'  // Language service uses 'TextAnalytics' kind
  properties: {
    customSubDomainName: languageName
    disableLocalAuth: false
  }
}

/*
  Azure Key Vault for secure secret storage
  Stores: API keys, endpoints, connection strings, etc.
*/
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true  // Use RBAC for access control
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true  // Set to true in production
  }
}

// =============================================================================
// SECRET STORAGE - Store credentials in Key Vault
// =============================================================================

/*
  Store Azure OpenAI endpoint as a secret
*/
resource openaiEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'AZURE-OPENAI-ENDPOINT'
  parent: keyVault
  properties: {
    value: 'https://${aiFoundry.properties.customSubDomainName}.services.ai.azure.com/openai/v1'
    contentType: 'text/plain'
  }
}

/*
  Store LLM Model Deployment Name as a secret
*/
resource llmModelSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'LLM-MODEL-DEPLOYMENT-NAME'
  parent: keyVault
  properties: {
    value: llmModelDeployment.name
    contentType: 'text/plain'
  }
}

/*
  Store Content Safety Endpoint as a secret
*/
resource contentSafetyEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'CONTENT-SAFETY-ENDPOINT'
  parent: keyVault
  properties: {
    value: 'https://${contentSafety.properties.customSubDomainName}.cognitiveservices.azure.com/'
    contentType: 'text/plain'
  }
}

/*
  Store Language Service Endpoint as a secret
*/
resource languageEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'LANGUAGE-ENDPOINT'
  parent: keyVault
  properties: {
    value: language.properties.endpoint
    contentType: 'text/plain'
  }
}

/*
  Store Language Service API Key as a secret
  IMPORTANT: Keys are sensitive and should never be in output logs
*/
resource languageKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'LANGUAGE-KEY'
  parent: keyVault
  properties: {
    value: language.listKeys().key1
    contentType: 'text/plain'
  }
}

output KEY_VAULT_ENDPOINT string = keyVault.properties.vaultUri
output KEY_VAULT_NAME string = keyVault.name
