output "gke_cluster_name" {
  description = "Created GKE Cluster Name"
  value       = module.gke.cluster_name
}

output "vertex_service_account_email" {
  description = "Service account email configured for Vertex AI"
  value       = google_service_account.vertex_ai_runner.email
}

output "workload_identity_pool" {
  description = "Configured Workload Identity Pool"
  value       = module.gke.workload_identity_pool
}
