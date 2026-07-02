//https://github.com/microsoft-foundry/foundry-samples/blob/main/infrastructure/infrastructure-setup-bicep/00-basic/main.bicep

param coursePrefix string
param aiFoundryName string = coursePrefix
param aiProjectName string = '${aiFoundryName}-proj'
param contentSafetyName string = '${coursePrefix}-csafety'
param redisName string = '${coursePrefix}-redis'
param cosmosDbAccountName string = '${coursePrefix}-cosmos'
param location string = resourceGroup().location
param llmModelDeploymentName string = '${coursePrefix}-llm-deploy'
param databaseName string = '${coursePrefix}-cosmosdb'
param containerName string = '${coursePrefix}-container'

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

/*
  Azure Cosmos DB for long-term conversation history storage
  Using Free Tier when available (25GB storage + 1000 RU/s free)
*/
resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: toLower(cosmosDbAccountName)  // Cosmos DB names must be lowercase
  location: location
  properties: {
    enableFreeTier: true               // FREE TIER ENABLED - 25GB + 1000 RU/s free
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'  // Perfect for conversation scenarios
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    enableAutomaticFailover: false      // Disabled for free tier optimization
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    capabilities: []                    // No additional capabilities for free tier
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: {
    environment: 'development'
    purpose: 'conversation-history-for-ai-agent'
  }
}

// Database for storing conversation history
resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosDbAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
    options: {
      throughput: 1000  // This will be FREE under the free tier (first 1000 RU/s)
    }
  }
}

// Container for conversation threads with optimized partition key for chat history
resource cosmosContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: [
          '/userId'     // Partition by user ID for efficient querying of user history
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'  // Index all fields for flexible querying
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'  // Exclude etag from indexing
          }
        ]
        // Add composite indexes for time-based queries
        compositeIndexes: [
          [
            {
              path: '/userId'
              order: 'ascending'
            }
            {
              path: '/timestamp'
              order: 'descending'
            }
          ]
        ]
      }
      // Optional: Add TTL for automatic cleanup of old conversations (90 days)
      defaultTtl: 7776000  // 90 days in seconds (comment out if you want to keep forever)
    }
  }
}

output OPENAI_ENDPOINT string = 'https://${aiFoundry.properties.customSubDomainName}.services.ai.azure.com/openai/v1'
output LLM_MODEL_DEPLOYMENT_NAME string = llmModelDeployment.name
output CONTENT_SAFETY_ENDPOINT string = 'https://${contentSafety.properties.customSubDomainName}.cognitiveservices.azure.com/'
output REDIS_HOSTNAME string = redisEnterprise.properties.hostName
output REDIS_PORT int = 10000
output REDIS_ACCESS_KEY string = redisDatabase.listKeys().primaryKey
output COSMOS_DB_ENDPOINT string = cosmosDbAccount.properties.documentEndpoint
output COSMOS_DB_NAME string = databaseName
output COSMOS_CONTAINER_NAME string = containerName
output COSMOS_PRIMARY_KEY string = cosmosDbAccount.listKeys().primaryMasterKey
