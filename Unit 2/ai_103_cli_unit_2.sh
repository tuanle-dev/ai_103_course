# First, create a resource group (if you haven't already)
az group create --name aiagent-course-rg --location eastus

# Deploy the Bicep file
az deployment group create --resource-group aiagent-course-rg --template-file ai_103_bicep_unit_2.bicep --parameters coursePrefix=unit2course

# Get your deployment outputs
az deployment group show --resource-group aiagent-course-rg --name ai_103_bicep_unit_2 --query properties.outputs

# Delete the entire deployment (So no more costs)
az group delete --name aiagent-course-rg --yes --no-wait

# Verify deletion of deployed resources
az group list --output table

# View recently deleted Cognitive Services accounts in the region (to confirm deletion)
az cognitiveservices account list-deleted --output table

# The following commands permanently delete the soft-deleted accounts.
az cognitiveservices account purge --location eastus --resource-group aiagent-course-rg --name unit2course
az cognitiveservices account purge --location eastus --resource-group aiagent-course-rg --name unit2course-csafety