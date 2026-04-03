terraform {
  required_version = ">= 1.6"

  required_providers {
    # https://registry.terraform.io/providers/lxc/incus/latest
    incus = {
      source  = "lxc/incus"
      version = ">= 0.3"
    }
  }
}

# Configure the Incus provider.
# By default it connects to the local Incus socket.
# Set INCUS_REMOTE, INCUS_SERVER_ADDRESS, INCUS_SERVER_CERT, etc. to connect
# to a remote Incus server.
provider "incus" {}
