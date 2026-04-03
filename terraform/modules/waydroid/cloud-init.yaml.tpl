#cloud-config
# Cloud-init script to install Waydroid on an Incus container host.
# Replaces the Anbox Cloud Appliance snap + amc toolchain.

package_update: true
package_upgrade: false

packages:
  - curl
  - ca-certificates
  - gnupg
  - lsb-release

%{ if ssh_public_key != "" ~}
ssh_authorized_keys:
  - ${ssh_public_key}
%{ endif ~}

runcmd:
  # Add Waydroid repository
  - curl -fsSL https://repo.waydro.id/waydroid.gpg | gpg --dearmor -o /usr/share/keyrings/waydroid.gpg
  - echo "deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydro.id/ $(lsb_release -sc) main" > /etc/apt/sources.list.d/waydroid.list
  - apt-get update -q
  - apt-get install -y waydroid

  # Install waydroid-toolkit for management
  - apt-get install -y python3-pip
  - pip3 install waydroid-toolkit

  # Initialize Waydroid with Android ${android_version}
  - waydroid init -f
  - systemctl enable --now waydroid-container

final_message: |
  Waydroid (Android ${android_version}) is installed and running.
  Connect via: wdt status
