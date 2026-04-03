# Terraform

Provisions Incus containers running Waydroid.

Located at `terraform/`.

Ported from [canonical/anbox-cloud-terraform](https://github.com/canonical/anbox-cloud-terraform).
Juju + `terraform-provider-juju` replaced with `terraform-provider-incus`.

## Requirements

- Terraform >= 1.6
- [lxc/incus provider](https://registry.terraform.io/providers/lxc/incus/latest) >= 0.3
- Incus installed and running on the target host

## Quick start

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

## Single host

```hcl
module "waydroid" {
  source           = "./terraform"
  incus_node_count = 1
  android_version  = "13"
}
```

## Multiple subclusters

```hcl
module "waydroid" {
  source = "./terraform"

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

## Variables

See [`terraform/variables.tf`](https://github.com/waydroid-toolkit/waydroid-toolkit/blob/main/terraform/variables.tf) for the full list.

Key variables:

| Variable | Default | Description |
|---|---|---|
| `waydroid_image` | `ubuntu:24.04` | Incus image |
| `incus_node_count` | `1` | Number of containers (flat mode) |
| `android_version` | `13` | Android version |
| `storage_size` | `20GiB` | Root disk per container |
| `enable_nfs` | `false` | Attach NFS share |
| `subclusters` | `[]` | Named container groups |

## Mapping from anbox-cloud-terraform

| Anbox | Waydroid |
|---|---|
| `terraform-provider-juju` | `terraform-provider-incus` |
| `lxd_node_count` | `incus_node_count` |
| `anbox_channel` | `waydroid_image` + `android_version` |
| Juju charm bundle | cloud-init script |
| `ubuntu_pro_token` | not required |
