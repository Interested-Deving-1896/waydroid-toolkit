variable "name" {
  description = "Container name."
  type        = string
}

variable "image" {
  description = "Incus image alias (e.g. ubuntu:24.04)."
  type        = string
  default     = "ubuntu:24.04"
}

variable "android_version" {
  description = "Android version for Waydroid (e.g. 13, 14, 15)."
  type        = string
  default     = "13"
}

variable "storage_pool" {
  description = "Incus storage pool for the root disk."
  type        = string
  default     = "default"
}

variable "storage_size" {
  description = "Root disk size (e.g. 20GiB)."
  type        = string
  default     = "20GiB"
}

variable "network_name" {
  description = "Incus network to attach to."
  type        = string
  default     = "incusbr0"
}

variable "ssh_public_key" {
  description = "SSH public key to inject via cloud-init."
  type        = string
  default     = ""
}

variable "enable_nfs" {
  description = "Attach an NFS disk device to this container."
  type        = bool
  default     = false
}

variable "nfs_source" {
  description = "NFS source path (host:/export)."
  type        = string
  default     = ""
}

variable "nfs_path" {
  description = "Mount point inside the container for the NFS share."
  type        = string
  default     = "/data/shared"
}
