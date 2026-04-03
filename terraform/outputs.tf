output "waydroid_containers" {
  description = "Names and IPv4 addresses of all provisioned Waydroid containers."
  value = {
    for k, m in module.waydroid : k => {
      name    = m.container_name
      address = m.ipv4_address
    }
  }
}
