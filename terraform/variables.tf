# Root-level variables for the Waydroid Terraform plan.
# Ported from canonical/anbox-cloud-terraform (Apache-2.0).
# Juju provider + anbox_channel replaced with incus provider + waydroid_image.
# lxd_node_count replaced with incus_node_count.

variable "waydroid_image" {
  description = "Incus image to use for Waydroid container hosts (e.g. ubuntu:24.04)."
  type        = string
  default     = "ubuntu:24.04"
}

variable "incus_node_count" {
  description = "Number of Incus container hosts to provision."
  type        = number
  default     = 1
}

variable "android_version" {
  description = "Android version for the Waydroid image (e.g. 13, 14, 15)."
  type        = string
  default     = "13"
}

variable "storage_pool" {
  description = "Incus storage pool to use for container root disks."
  type        = string
  default     = "default"
}

variable "storage_size" {
  description = "Root disk size for each Waydroid container (e.g. 20GiB)."
  type        = string
  default     = "20GiB"
}

variable "network_name" {
  description = "Incus network to attach containers to."
  type        = string
  default     = "incusbr0"
}

variable "ssh_public_key" {
  description = "SSH public key to inject into container hosts (cloud-init)."
  type        = string
  default     = ""
}

variable "enable_nfs" {
  description = "Attach an NFS share to each Waydroid container."
  type        = bool
  default     = false
}

variable "nfs_source" {
  description = "NFS source path (host:/export) when enable_nfs = true."
  type        = string
  default     = ""
}

variable "nfs_container_path" {
  description = "Mount point inside the container for the NFS share."
  type        = string
  default     = "/data/shared"
}

variable "subclusters" {
  description = "List of named Waydroid subclusters to deploy."
  type = list(object({
    name             = string
    incus_node_count = number
    enable_nfs       = optional(bool, false)
    nfs_source       = optional(string, "")
  }))
  default = []
}
