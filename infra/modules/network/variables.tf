variable "append_workspace" {
  description = "Appends the terraform workspace at the end of resource names, <identifier>-<workspace>"
  default     = true
  type        = bool
}

variable "app" {
  description = "(Required) Name of the network resources"
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

variable "nat_gateway_zones" {
  description = "(Required) The list of availability zones to create the NAT gateway and public IP address in"
  type = list(string)
  default = null
}