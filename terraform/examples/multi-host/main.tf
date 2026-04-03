# Multi-host Waydroid deployment example.
# Mirrors the anbox-cloud-terraform subcluster model, using Incus instead of Juju/LXD.
# Each subcluster is a named group of Incus containers running Waydroid.

module "waydroid" {
  source = "../../"

  android_version = "13"
  storage_size    = "20GiB"

  subclusters = [
    {
      name             = "alpha"
      incus_node_count = 2
      enable_nfs       = true
      nfs_source       = "192.168.1.10:/exports/assets"
    },
    {
      name             = "beta"
      incus_node_count = 1
    },
  ]
}

output "containers" {
  value = module.waydroid.waydroid_containers
}
