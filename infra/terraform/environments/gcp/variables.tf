variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "Default GCP Region"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "Aegis GKE Cluster Name"
  type        = string
  default     = "aegis-prod-gke"
}

variable "k8s_namespace" {
  description = "Kubernetes namespace for Aegis workloads"
  type        = string
  default     = "aegis-system"
}

variable "k8s_service_account" {
  description = "Kubernetes Service Account name"
  type        = string
  default     = "aegis-control-plane-sa"
}
