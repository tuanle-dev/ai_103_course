# First, create a resource group (if you haven't already)
az group create --name aiagent-course-rg --location australiaeast

# Deploy the Bicep file
az deployment group create --resource-group aiagent-course-rg --template-file ai_103_bicep_unit_19.bicep --parameters coursePrefix=unit19course

# Get your deployment outputs
az deployment group show --resource-group aiagent-course-rg --name ai_103_bicep_unit_19 --query properties.outputs

# Get the object ID of the currently signed-in user
az ad signed-in-user show --query id -o tsv

# Assign the "Key Vault Secrets User" role to the user for the Key Vault resource
az role assignment create --assignee-object-id "1c84ee91-d668-45fe-8b94-56a74ac97b03" --assignee-principal-type "User" --role "Key Vault Secrets User" --scope "/subscriptions/b4272717-b8f9-4c65-8d2e-fc113f928034/resourceGroups/aiagent-course-rg/providers/Microsoft.KeyVault/vaults/unit19course-kvault"

# Delete the entire deployment (So no more costs)
az group delete --name aiagent-course-rg --yes --no-wait

# Verify deletion of deployed resources
az group list --output table

# View recently deleted Cognitive Services accounts in the region (to confirm deletion)
az cognitiveservices account list-deleted --output table

# The following commands permanently delete the soft-deleted accounts.
az cognitiveservices account purge --location australiaeast --resource-group aiagent-course-rg --name unit19course
az cognitiveservices account purge --location australiaeast --resource-group aiagent-course-rg --name unit19course-csafety
az cognitiveservices account purge --location australiaeast --resource-group aiagent-course-rg --name unit19course-language

# Find all soft-deleted Key Vaults in the region (to confirm deletion)
az keyvault list-deleted

# Find when the key vault will be permanently deleted (scheduled purge date)
az keyvault list-deleted --resource-type vault --query "[?name=='unit19course-kvault'].properties.scheduledPurgeDate"

# (NO LONDER WORKERS) The following command permanently deletes the soft-deleted Key Vault.
az keyvault purge --name unit19course-kvault --location australiaeast