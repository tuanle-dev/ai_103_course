# Step 1: Create a new environment
python -m venv tutorials

# Step 2: Identify the new environment's Python executable path
tutorials\Scripts\activate

# Step 3: Use the cloned requirements.txt file to install dependencies
pip install -r requirements.txt

# Step 4: Generate the requirements.txt file with the package versions
pip freeze > requirements.txt

# Step 5: Ensure the debugger is using the environment's Python executable path

# Step 6: Download and install the Azure CLI from https://aka.ms/installazurecli and then restart VSCode

# Step 7: Authenticate to Azure using CLI
az login