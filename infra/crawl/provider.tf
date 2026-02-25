# 1. Specify the version of the AzureRM provider and Databricks provider to use
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "3.0.1"
    }
  }
  backend "azurerm" {
    resource_group_name  = "stateResourceGroup"
    storage_account_name = "tfstatesall"
    container_name       = "tfstates-storage"
    key                  = "crawl.tfstate"
  }

}

# 2. Configure the AzureRM Provider
provider "azurerm" {
  # The AzureRM Provider supports authenticating using via the Azure CLI, a Managed Identity
  # and a Service Principal. More information on the authentication methods supported by
  # the AzureRM Provider can be found here:
  # https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs#authenticating-to-azure

  # The features block allows changing the behaviour of the Azure Provider, more
  # information can be found here:
  # https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/guides/features-block
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}
