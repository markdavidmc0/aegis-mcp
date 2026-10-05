terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region

  network    = var.network
  subnetwork = var.subnetwork

  # Enable Dataplane V2 (Cilium)
  datapath_provider = "ADVANCED_DATAPATH"

  # Enable Workload Identity Federation
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # We remove default node pool and manage custom pools
  remove_default_node_pool = true
  initial_node_count       = 1

  release_channel {
    channel = "REGULAR"
  }

  ip_allocation_policy {}

  addons_config {
    network_policy_config {
      disabled = false
    }
  }
}

resource "google_container_node_pool" "gvisor_sandbox_nodes" {
  name       = "${var.cluster_name}-gvisor-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.gvisor_node_count

  node_config {
    machine_type = var.machine_type
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Enable gVisor sandbox container runtime (runsc)
    sandbox_config {
      sandbox_type = "gvisor"
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    labels = {
      "sandbox.gke.io/runtime" = "gvisor"
      "aegis.io/role"           = "dataplane-sandbox"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
