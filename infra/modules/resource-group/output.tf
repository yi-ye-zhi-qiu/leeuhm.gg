output "output" {
  value = {
    resource_group_id       = azurerm_resource_group.rg.id
    resource_group_name     = azurerm_resource_group.rg.name
    resource_group_location = azurerm_resource_group.rg.location
  }
}