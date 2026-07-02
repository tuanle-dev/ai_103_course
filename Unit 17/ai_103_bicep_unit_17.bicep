//https://github.com/microsoft-foundry/foundry-samples/blob/main/infrastructure/infrastructure-setup-bicep/00-basic/main.bicep

param coursePrefix string
param aiFoundryName string = coursePrefix
param aiProjectName string = '${aiFoundryName}-proj'
param contentSafetyName string = '${coursePrefix}-csafety'
param visionName string = '${coursePrefix}-vision'
param speechName string = '${coursePrefix}-speech'
param docIntelName string = '${coursePrefix}-docintel'
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
  Azure AI Vision service for image analysis (including OCR, captioning, and multimodal analysis)
*/
resource vision 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: visionName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'F0' // Free tier, change to 'S0' for production use (removing free tier limits and allowing SLA)
  }
  kind: 'ComputerVision'
  properties: {
    customSubDomainName: visionName
    disableLocalAuth: false
  }
}

/*
  Azure AI Speech service for speech-to-text, text-to-speech, and speech translation
*/
resource speech 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: speechName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'F0'
  }
  kind: 'SpeechServices'
  properties: {
    customSubDomainName: speechName
    disableLocalAuth: false
  }
}

/*
  Azure AI Document Intelligence service for document processing (forms, invoices, receipts, etc.)
*/
resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: docIntelName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'F0'
  }
  kind: 'FormRecognizer'
  properties: {
    customSubDomainName: docIntelName
    disableLocalAuth: false
  }
}


output OPENAI_ENDPOINT string = 'https://${aiFoundry.properties.customSubDomainName}.services.ai.azure.com/openai/v1'
output LLM_MODEL_DEPLOYMENT_NAME string = llmModelDeployment.name
output CONTENT_SAFETY_ENDPOINT string = 'https://${contentSafety.properties.customSubDomainName}.cognitiveservices.azure.com/'
output VISION_ENDPOINT string = vision.properties.endpoint
output SPEECH_REGION string = location
output DOC_INTEL_ENDPOINT string = documentIntelligence.properties.endpoint
output VISION_KEY string = vision.listKeys().key1
output SPEECH_KEY string = speech.listKeys().key1
output DOC_INTEL_KEY string = documentIntelligence.listKeys().key1
