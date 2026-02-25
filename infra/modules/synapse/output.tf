output "output" {
  value = {
    synapse_workspace_id     = azurerm_synapse_workspace.workspace.id
    synapse_workspace_name   = azurerm_synapse_workspace.workspace.name
    connectivity_endpoints   = azurerm_synapse_workspace.workspace.connectivity_endpoints
    adls_storage_account_name = azurerm_storage_account.adls.name
  }
}
