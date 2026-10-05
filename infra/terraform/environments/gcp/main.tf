terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. GKE Cluster with gVisor sandbox pool and Cilium Dataplane V2
module "gke" {
  source       = "../../modules/gke_gvisor"
  project_id   = var.project_id
  cluster_name = var.cluster_name
  region       = var.region
}

# 2. Google Service Account (GSA) for Vertex AI Access
resource "google_service_account" "vertex_ai_runner" {
  account_id   = "aegis-vertex-ai-runner"
  display_name = "Aegis Vertex AI Runner Service Account"
  project      = var.project_id
}

# Grant Vertex AI User role to GSA
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.vertex_ai_runner.email}"
}

# 3. Workload Identity Federation (WIF): Bind Kubernetes Service Account (KSA) to GSA
resource "google_service_account_iam_member" "workload_identity_binding" {
  service_account_id = google_service_account.vertex_ai_runner.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.k8s_namespace}/${var.k8s_service_account}]"
}
