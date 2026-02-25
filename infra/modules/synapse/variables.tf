variable "append_workspace" {
  description = "Appends the terraform workspace at the end of resource names, <identifier>-<workspace>"
  default     = true
  type        = bool
}

variable "app" {
  description = "(Required) Name of the Synapse resources"
  type        = string
}

variable "resource_group_name" {
  description = "(Required) Name of the Azure resource group"
  type        = string
}

variable "resource_group_location" {
  description = "(Required) Location of the Azure resource group"
  type        = string
}

variable "sql_administrator_login" {
  description = "(Required) SQL administrator login name"
  type        = string
}

variable "sql_administrator_login_password" {
  description = "(Required) SQL administrator login password"
  type        = string
  sensitive   = true
}

variable "crawl_storage_account_id" {
  description = "(Required) Resource ID of the crawl storage account to grant Synapse read access"
  type        = string
}
