locals {
  app = var.append_workspace ? "${var.app}${title(terraform.workspace)}" : var.app
}

# ADLS Gen2 storage account for Synapse metadata (HNS enabled)
resource "azurerm_storage_account" "adls" {
  name                     = "${local.app}adls"
  resource_group_name      = var.resource_group_name
  location                 = var.resource_group_location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
}

# Filesystem in the ADLS Gen2 account
resource "azurerm_storage_data_lake_gen2_filesystem" "fs" {
  name               = "${local.app}fs"
  storage_account_id = azurerm_storage_account.adls.id
}

# Synapse workspace (serverless SQL pool is built-in)
resource "azurerm_synapse_workspace" "workspace" {
  name                                 = "${local.app}-ws"
  resource_group_name                  = var.resource_group_name
  location                             = var.resource_group_location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.fs.id
  sql_administrator_login              = var.sql_administrator_login
  sql_administrator_login_password     = var.sql_administrator_login_password

  identity {
    type = "SystemAssigned"
  }
}

# Firewall rule — allow all IPs (dev only)
resource "azurerm_synapse_firewall_rule" "allow_all" {
  name                 = "AllowAll"
  synapse_workspace_id = azurerm_synapse_workspace.workspace.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "255.255.255.255"
}

# Grant Synapse identity Storage Blob Data Contributor on crawl storage
resource "azurerm_role_assignment" "synapse_crawl_storage" {
  scope                = var.crawl_storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_synapse_workspace.workspace.identity[0].principal_id
}

# Grant Synapse identity Storage Blob Data Contributor on its own ADLS
resource "azurerm_role_assignment" "synapse_adls_storage" {
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_synapse_workspace.workspace.identity[0].principal_id
}
