output "synapse_serverless_sql_endpoint" {
  value = module.synapse.output.connectivity_endpoints["sqlOnDemand"]
}

output "synapse_workspace_name" {
  value = module.synapse.output.synapse_workspace_name
}
