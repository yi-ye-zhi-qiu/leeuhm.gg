output "output" {
  value = {
    repository_username = azurerm_container_registry.acr.admin_username
    repository_password = azurerm_container_registry.acr.admin_password
    repository_server   = azurerm_container_registry.acr.login_server
    repository_id       = azurerm_container_registry.acr.id
  }
}