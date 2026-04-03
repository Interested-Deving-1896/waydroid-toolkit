# Waydroid Terraform

Terraform plan to provision Incus containers running Waydroid.

Ported from [canonical/anbox-cloud-terraform](https://github.com/canonical/anbox-cloud-terraform).
Juju + `terraform-provider-juju` replaced with `terraform-provider-incus`.
Anbox Cloud charms replaced with cloud-init scripts that install Waydroid.

## Requirements

| Name | Version |
|---|---|
| terraform | >= 1.6 |
| [lxc/incus](https://registry.terraform.io/providers/lxc/incus/latest) | >= 0.3 |

Incus must be installed and running on the target host(s).

## Inputs

| Name | Default | Description |
|---|---|---|
| `waydroid_image` | `ubuntu:24.04` | Incus image for container hosts |
| `incus_node_count` | `1` | Number of containers (flat mode) |
| `android_version` | `13` | Android version for Waydroid |
| `storage_pool` | `default` | Incus storage pool |
| `storage_size` | `20GiB` | Root disk size per container |
| `network_name` | `incusbr0` | Incus network |
| `ssh_public_key` | `""` | SSH key injected via cloud-init |
| `enable_nfs` | `false` | Attach NFS share to containers |
| `nfs_source` | `""` | NFS path (host:/export) |
| `subclusters` | `[]` | Named groups of containers (see below) |

## Usage

### Single host

```hcl
module "waydroid" {
  source           = "github.com/waydroid-toolkit/waydroid-toolkit//terraform"
  incus_node_count = 1
  android_version  = "13"
}
```

### Multiple named subclusters

```hcl
module "waydroid" {
  source = "github.com/waydroid-toolkit/waydroid-toolkit//terraform"

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
```

```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

## Mapping from anbox-cloud-terraform

| Anbox | Waydroid |
|---|---|
| `terraform-provider-juju` | `terraform-provider-incus` |
| `lxd_node_count` | `incus_node_count` |
| `anbox_channel` | `waydroid_image` + `android_version` |
| Juju charm bundle | cloud-init script |
| `juju_integration` cross-model relations | Incus network bridges |
| `ubuntu_pro_token` | not required |
