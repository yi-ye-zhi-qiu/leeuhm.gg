# brew update && brew install azure-cli
# az login

# 1. Deploy root infra (state storage)
# cd infra/root/
# terraform init
# terraform apply

# 2. Deploy crawl infra
# cd infra/crawl/
# terraform init
# terraform workspace new dev
# terraform apply

# 3. Deploy database infra (Synapse)
# cd infra/db/
# terraform init
# terraform workspace new dev
# terraform apply -var="synapse_sql_password=<YOUR_PASSWORD>"

# 4. Configure GitHub Actions for ACR deployment
cd infra/crawl/
APP_CLIENT_ID=$(terraform output -raw app_client_id)
APP_PASSWORD=$(terraform output -raw app_password)
ACR_LOGIN_SERVER=$(az acr list --query "[].loginServer" -o tsv)

gh secret set AZURE_REGISTRY --body "$ACR_LOGIN_SERVER"
gh secret set AZURE_CLIENT_ID --body "$APP_CLIENT_ID"
gh secret set AZURE_CLIENT_SECRET --body "$APP_PASSWORD"

# 5. Set up Synapse database (one-time: creates crawldb, master key, credential, data source)
cd ../../db/
pip install -r requirements.txt
SYNAPSE_PASSWORD='<YOUR_PASSWORD>' python3 setup.py
