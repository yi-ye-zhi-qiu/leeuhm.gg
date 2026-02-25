# Output the Service Principal client id and password
# You can run e.g. `terraform output app_id` to view app id

# Identical to below CLI command:
# az ad sp list --display-name $SERVICE_PRINCIPAL_NAME --query "[].appId" --output tsv
output "app_client_id" {
    value  =  azuread_application.app.client_id
    sensitive  =  true
}

output "app_password" {
    value  =  azuread_application_password.key.value
    sensitive  =  true
}

# The IP address that you can whitelist in whatever proxy service you use
output "ip_address" {
    value = module.networking.output.ip_address
    sensitive = true
}

# Storage outputs (consumed by infra/db/ via remote state)
output "storage_account_name" {
    value = module.storage_container.output.storage_account_name
}

output "storage_account_id" {
    value = module.storage_container.output.storage_account_id
}

output "storage_container_name" {
    value = module.storage_container.output.storage_container_name
}

output "resource_group_name" {
    value = module.resource_group.output.resource_group_name
}

output "resource_group_location" {
    value = module.resource_group.output.resource_group_location
}
