output "output" {
  value = {
    storage_container_name             = azurerm_storage_container.storage_container.name
    storage_account_name               = azurerm_storage_account.storage_acc.name
    storage_account_id                 = azurerm_storage_account.storage_acc.id
    storage_account_primary_access_key = azurerm_storage_account.storage_acc.primary_access_key
  }
}