# This file creates a container instance that runs `run.sh` in the 
# crawler repository image. This launches in a virtual network
# with a private subnet routed to a NAT gatway associated with 
# a public IP address.
# 
# This is loosely based off of these resources:
# - Quickstart: https://learn.microsoft.com/en-us/azure/container-instances/container-instances-quickstart-terraform
# - Using a VNet: https://truestorydavestorey.medium.com/how-to-get-an-azure-container-instance-running-inside-a-vnet-with-a-fileshare-mount-using-terraform-a12f5b2b86ce

locals {
  app = var.append_workspace ? "${var.app}${title(terraform.workspace)}" : var.app
}


resource "azurerm_log_analytics_workspace" "logs" {
  name                = "${local.app}LogAnalytics"
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018" # This is the default value
  retention_in_days   = 30 # Minimum value of options (30 - 730)
}

resource "azurerm_container_group" "task" {
  name                = local.app
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  network_profile_id  = var.network_profile_id
  
  # Give permissions to read from ACR repository
  image_registry_credential {
    username = var.repository_login_username
    password = var.repository_login_password
    server   = var.repository_login_server
  }

  # Create a log analytics workspace for containers
  diagnostics {
    log_analytics {
     log_type      = "ContainerInsights"
      workspace_id  = azurerm_log_analytics_workspace.logs.workspace_id
      workspace_key = azurerm_log_analytics_workspace.logs.primary_shared_key
      metadata      = {}
    }
  }

  ip_address_type = "Private"

  # The restart policy parameter ensures that when the container finishes,
  # it will not restart again. In practice, this means that after the
  # command runs, it will shut down.
  restart_policy = "OnFailure"

  container {
    name                  = var.container_name
    image                 = "${var.repository_login_server}/${var.image_name}:${var.image_tag}"
    cpu                   = "0.5"
    memory                = "1.5"
    environment_variables = {      
      "AZURE_CONTAINER"   = var.azure_storage_container      
      "AZURE_ACCOUNT_URL" = "https://${var.azure_account_url}.blob.core.windows.net/"
      "AZURE_ACCOUNT_KEY" = var.azure_account_key
    }
    # Run the shellscript in the `crawler` repository that triggers
    # code to run.
    commands              = ["sh", "run.sh"]

    # I am not sure why this is needed but else we get the error:
    # The ports in the 'ipAddress' of container group 'crawlerTaskDev' cannot be empty
    ports {
      port     = 8000
      protocol = "TCP"
    }
  }
}
