# First, create a resource group (if you haven't already)
az group create --name aiagent-course-rg --location australiaeast

# Deploy the Bicep file
az deployment group create --resource-group aiagent-course-rg --template-file ai_103_bicep_unit_14.bicep --parameters coursePrefix=unit14course2

# Get your deployment outputs
az deployment group show --resource-group aiagent-course-rg --name ai_103_bicep_unit_14 --query properties.outputs

# Delete the entire deployment (So no more costs)
az group delete --name aiagent-course-rg --yes --no-wait

# Verify deletion of deployed resources
az group list --output table

# View recently deleted Cognitive Services accounts in the region (to confirm deletion)
az cognitiveservices account list-deleted --output table

# The following commands permanently delete the soft-deleted accounts.
az cognitiveservices account purge --location australiaeast --resource-group aiagent-course-rg --name unit14course
az cognitiveservices account purge --location australiaeast --resource-group aiagent-course-rg --name unit14course-csafety