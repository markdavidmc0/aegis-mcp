output "cluster_name" {
  description = "The name of the created GKE cluster"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "Cluster endpoint IP"
  value       = google_container_cluster.primary.endpoint
}

output "ca_certificate" {
  description = "Cluster master CA certificate"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "workload_identity_pool" {
  description = "GKE Workload Identity Pool"
  value       = "${var.project_id}.svc.id.goog"
}
