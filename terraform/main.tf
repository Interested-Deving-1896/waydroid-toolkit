# Waydroid Terraform plan — provisions Incus containers running Waydroid.
#
# Ported from canonical/anbox-cloud-terraform (Apache-2.0).
# Juju + terraform-provider-juju replaced with terraform-provider-incus.
# Anbox Cloud charms replaced with cloud-init scripts that install Waydroid.
# lxd_node_count → incus_node_count.
# anbox_channel → waydroid_image + android_version.
#
# Usage:
#   terraform init
#   terraform plan -out=tfplan -var-file=waydroid.tfvars
#   terraform apply tfplan

locals {
  # Build a flat map of all nodes across all subclusters.
  # Each key is "<subcluster>-<index>" for unique naming.
  subcluster_nodes = length(var.subclusters) > 0 ? {
    for pair in flatten([
      for sc in var.subclusters : [
        for i in range(sc.incus_node_count) : {
          key        = "${sc.name}-${i}"
          subcluster = sc.name
          index      = i
          enable_nfs = sc.enable_nfs
          nfs_source = sc.nfs_source
        }
      ]
    ]) : pair.key => pair
  } : {}

  # When no subclusters are defined, fall back to the flat node count.
  flat_nodes = length(var.subclusters) == 0 ? {
    for i in range(var.incus_node_count) : "waydroid-${i}" => {
      key        = "waydroid-${i}"
      subcluster = "default"
      index      = i
      enable_nfs = var.enable_nfs
      nfs_source = var.nfs_source
    }
  } : {}

  all_nodes = merge(local.subcluster_nodes, local.flat_nodes)
}

module "waydroid" {
  for_each = local.all_nodes
  source   = "./modules/waydroid"

  name           = each.key
  image          = var.waydroid_image
  android_version = var.android_version
  storage_pool   = var.storage_pool
  storage_size   = var.storage_size
  network_name   = var.network_name
  ssh_public_key = var.ssh_public_key
  enable_nfs     = each.value.enable_nfs
  nfs_source     = each.value.nfs_source
  nfs_path       = var.nfs_container_path
}
