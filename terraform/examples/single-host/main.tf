# Single-host Waydroid deployment example.
# Provisions one Incus container running Waydroid.

module "waydroid" {
  source = "../../"

  incus_node_count = 1
  android_version  = "13"
  storage_size     = "20GiB"
}

output "containers" {
  value = module.waydroid.waydroid_containers
}
