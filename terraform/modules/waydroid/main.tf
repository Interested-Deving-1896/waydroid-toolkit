# Waydroid container module.
#
# Provisions a single Incus container with Waydroid installed via cloud-init.
# Replaces the Anbox Cloud subcluster Juju charm bundle.

terraform {
  required_providers {
    incus = {
      source  = "lxc/incus"
      version = ">= 0.3"
    }
  }
}

locals {
  cloud_init = templatefile("${path.module}/cloud-init.yaml.tpl", {
    android_version = var.android_version
    ssh_public_key  = var.ssh_public_key
  })
}

resource "incus_instance" "waydroid" {
  name  = var.name
  image = var.image
  type  = "container"

  config = {
    "boot.autostart"       = "true"
    "security.nesting"     = "true"   # required for Waydroid LXC-in-LXC
    "security.privileged"  = "false"
    "user.user-data"       = local.cloud_init
  }

  device {
    name = "root"
    type = "disk"
    properties = {
      pool = var.storage_pool
      path = "/"
      size = var.storage_size
    }
  }

  device {
    name = "eth0"
    type = "nic"
    properties = {
      network = var.network_name
    }
  }

  # Optional NFS share — mirrors the anbox-cloud-nfs-operator charm behaviour.
  dynamic "device" {
    for_each = var.enable_nfs && var.nfs_source != "" ? [1] : []
    content {
      name = "nfs-shared"
      type = "disk"
      properties = {
        source               = var.nfs_source
        path                 = var.nfs_path
        "raw.mount.options"  = "soft,async"
      }
    }
  }
}
