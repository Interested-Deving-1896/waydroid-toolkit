output "container_name" {
  description = "Name of the provisioned Incus container."
  value       = incus_instance.waydroid.name
}

output "ipv4_address" {
  description = "IPv4 address of the container (may be empty until cloud-init completes)."
  value       = try(incus_instance.waydroid.ipv4_address, "")
}
