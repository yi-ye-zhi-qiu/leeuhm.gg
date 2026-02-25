output "output" {
  value = {
    vnet               = azurerm_virtual_network.vnet.id
    ip_address         = azurerm_public_ip.pip.ip_address
    network_profile_id = azurerm_network_profile.network_profile.id
  }
}