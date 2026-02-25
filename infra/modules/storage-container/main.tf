locals {
  app = var.append_workspace ? "${var.app}${title(terraform.workspace)}" : var.app
}


resource "azurerm_storage_account" "storage_acc" {
  name                     = "${local.app}acc"
  resource_group_name      = var.resource_group_name
  location                 = var.resource_group_location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "storage_container" {
  name                  = local.app
  storage_account_name  = azurerm_storage_account.storage_acc.name
  container_access_type = "private"
}
