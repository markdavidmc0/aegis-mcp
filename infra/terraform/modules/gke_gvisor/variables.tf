variable "project_id" {
  description = "The GCP Project ID to host the cluster in"
  type        = string
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
  default     = "aegis-gke-prod"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "network" {
  description = "VPC network name"
  type        = string
  default     = "default"
}

variable "subnetwork" {
  description = "VPC subnetwork name"
  type        = string
  default     = "default"
}

variable "gvisor_node_count" {
  description = "Number of sandboxed gVisor runner nodes"
  type        = number
  default     = 3
}

variable "machine_type" {
  description = "Compute instance machine type for sandbox nodes"
  type        = string
  default     = "e2-standard-4"
}
