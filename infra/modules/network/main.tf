locals {
  app = var.append_workspace ? "${var.app}${title(terraform.workspace)}" : var.app
}


# Create the NAT gateway
resource "azurerm_nat_gateway" "nat" {
  name                    = "${local.app}NatGateway"
  location                = var.resource_group_location
  resource_group_name     = var.resource_group_name
  sku_name                = "Standard"
  idle_timeout_in_minutes = 10
  zones                   = var.nat_gateway_zones
}

# Static IP address for outbound traffic
resource "azurerm_public_ip" "pip" {
  name                = "${local.app}Pip"
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = var.nat_gateway_zones
}

# Association between a NAT gateway and a public IP 
resource "azurerm_nat_gateway_public_ip_association" "nat_public_ip_association" {
  nat_gateway_id       = azurerm_nat_gateway.nat.id
  public_ip_address_id = azurerm_public_ip.pip.id
}

# Route traffic in private subnets to NAT gateway

# Create virtual network
resource "azurerm_virtual_network" "vnet" {
  name                = "${local.app}Vnet"
  address_space       = ["10.0.0.0/16"]
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name
}

# Create subnet
resource "azurerm_subnet" "private_subnet" {
  name                 = "${local.app}PrivateSubnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.ContainerInstance/containerGroups"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action"
      ]
    }
  }
}

# Associate NAT gateway with subnet
resource "azurerm_subnet_nat_gateway_association" "main" {
  nat_gateway_id = azurerm_nat_gateway.nat.id
  subnet_id      = azurerm_subnet.private_subnet.id
}

# This is the network profile used by containers
resource "azurerm_network_profile" "network_profile" {
  name                = "${local.app}NetworkProfile"
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name

  container_network_interface {
    name = "${local.app}NetworkInterface"

    ip_configuration {
      name      = "${local.app}IpConfig"
      subnet_id = azurerm_subnet.private_subnet.id
    }
  }
}