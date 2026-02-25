variable "append_workspace" {
  description = "Appends the terraform workspace at the end of resource names, <identifier>-<workspace>"
  default     = true
  type        = bool
}

variable "app" {
  description = "(Required) Name of the Azure resource group"
  type        = string
}

variable "region" {
  description = "(Required) The Azure Region where the Resource Group should exist"
  type        = string
}