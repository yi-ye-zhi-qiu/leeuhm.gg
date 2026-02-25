locals {
  app = var.append_workspace ? "${var.app}${title(terraform.workspace)}" : var.app
}

resource "azurerm_resource_group" "rg" {
  name     = local.app
  location = var.region
}