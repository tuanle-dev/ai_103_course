# First, create a resource group (if you haven't already)
az group create --name aiagent-course-rg --location australiaeast

# Deploy the Bicep file
az deployment group create --resource-group aiagent-course-rg --template-file ai_103_bicep_unit_6.bicep --parameters coursePrefix=unit6course

# Get your deployment outputs
az deployment group show --resource-group aiagent-course-rg --name ai_103_bicep_unit_6 --query properties.outputs

# Get the object ID of the currently signed-in user
az ad signed-in-user show --query id -o tsv

# Assign the "Search Service Contributor" role to the user for the Azure AI Search resource
az role assignment create --assignee-object-id "OBJECT_ID_INSERT_HERE" --assignee-principal-type "User" --role "Search Service Contributor" --scope "/subscriptions/SUBSCRIPTION_ID_INSERT_HERE/resourceGroups/RESOURCE_GROUP_INSERT_HERE/providers/Microsoft.Search/searchServices/unit6course-aisearch"

# Assign the "Search Index Data Contributor" role to the user for the Azure AI Search resource
az role assignment create --assignee-object-id "OBJECT_ID_INSERT_HERE" --assignee-principal-type "User" --role "Search Index Data Contributor" --scope "/subscriptions/SUBSCRIPTION_ID_INSERT_HERE/resourceGroups/RESOURCE_GROUP_INSERT_HERE/providers/Microsoft.Search/searchServices/unit6course-aisearch"

# Assign the "Search Index Data Reader" role to the user for the Azure AI Search resource
az role assignment create --assignee-object-id "OBJECT_ID_INSERT_HERE" --assignee-principal-type "User" --role "Search Index Data Reader" --scope "/subscriptions/SUBSCRIPTION_ID_INSERT_HERE/resourceGroups/RESOURCE_GROUP_INSERT_HERE/providers/Microsoft.Search/searchServices/unit6course-aisearch"

# Delete the entire deployment (So no more costs)
az group delete --name aiagent-course-rg --yes --no-wait

# Verify deletion of deployed resources
az group list --output table

# View recently deleted Cognitive Services accounts in the region (to confirm deletion)
az cognitiveservices account list-deleted --output table

# The following commands permanently delete the soft-deleted accounts.
az cognitiveservices account purge --location australiaeast --resource-group aiagent-course-rg --name unit6course