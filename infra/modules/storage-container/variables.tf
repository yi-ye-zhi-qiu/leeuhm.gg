variable "append_workspace" {
  description = "Appends the terraform workspace at the end of resource names, <identifier>-<workspace>"
  default     = true
  type        = bool
}

variable "app" {
  description = "(Required) Name of the Azure Container task"
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