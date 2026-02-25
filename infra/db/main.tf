data "terraform_remote_state" "crawl" {
  backend   = "azurerm"
  workspace = terraform.workspace
  config = {
    resource_group_name  = "stateResourceGroup"
    storage_account_name = "tfstatesall"
    container_name       = "tfstates-storage"
    key                  = "crawl.tfstate"
  }
}

module "synapse" {
  source = "../modules/synapse"

  append_workspace                 = false
  app                              = "crawlsynapse"
  resource_group_name              = data.terraform_remote_state.crawl.outputs.resource_group_name
  resource_group_location          = data.terraform_remote_state.crawl.outputs.resource_group_location
  sql_administrator_login          = "sqladmin"
  sql_administrator_login_password = var.synapse_sql_password
  crawl_storage_account_id         = data.terraform_remote_state.crawl.outputs.storage_account_id
}
