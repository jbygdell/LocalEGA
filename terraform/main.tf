/* ===================================
   Main file for the Local EGA project
   =================================== */

variable os_username {}
variable os_password {}
variable db_password {}
variable pubkey {}

variable rsa_home {}
variable gpg_home {}
variable gpg_certs {}
variable gpg_passphrase {}
variable lega_conf {}
variable cidr { default = "192.168.10.0/24" }

# Configure the OpenStack Provider
provider "openstack" {
  user_name   = "${var.os_username}"
  password    = "${var.os_password}"
  tenant_id   = "e62c28337a094ea99571adfb0b97939f"
  tenant_name = "SNIC 2017/13-34"
  auth_url    = "https://hpc2n.cloud.snic.se:5000/v3"
  region      = "HPC2N"
  domain_name = "snic"
}

# ========= Network =========
resource "openstack_networking_network_v2" "ega_net" {
  name           = "ega_net"
  admin_state_up = "true"
}

resource "openstack_networking_subnet_v2" "ega_subnet" {
  network_id  = "${openstack_networking_network_v2.ega_net.id}"
  name        = "ega_subnet"
  cidr        = "${var.cidr}"
  enable_dhcp = true
  ip_version  = 4
  dns_nameservers = ["130.239.1.90","8.8.8.8"]
}

resource "openstack_networking_router_interface_v2" "ega_router_interface" {
  router_id = "1f852a3d-f7ea-45ae-9cba-3160c2029ba1"
  subnet_id = "${openstack_networking_subnet_v2.ega_subnet.id}"
}

# ========= Key Pair =========
resource "openstack_compute_keypair_v2" "ega_key" {
  name       = "ega_key"
  public_key = "${var.pubkey}"
}

# ========= Instances as Modules =========
module "db" {
  source = "./instances/db"
  db_password = "${var.db_password}"
  private_ip = "192.168.10.10"
  ega_key = "${openstack_compute_keypair_v2.ega_key.name}"
  ega_net = "${openstack_networking_network_v2.ega_net.id}"
}
module "mq" {
  source = "./instances/mq"
  private_ip = "192.168.10.11"
  ega_key = "${openstack_compute_keypair_v2.ega_key.name}"
  ega_net = "${openstack_networking_network_v2.ega_net.id}"
}
module "connectors" {
  source = "./instances/connectors"
  private_ip = "192.168.10.13"
  ega_key = "${openstack_compute_keypair_v2.ega_key.name}"
  ega_net = "${openstack_networking_network_v2.ega_net.id}"
  lega_conf = "${base64encode("${file("${var.lega_conf}")}")}"
}
module "inbox" {
  source = "./instances/inbox"
  volume_size = 600
  db_password = "${var.db_password}"
  private_ip = "192.168.10.14"
  ega_key = "${openstack_compute_keypair_v2.ega_key.name}"
  ega_net = "${openstack_networking_network_v2.ega_net.id}"
  lega_conf = "${base64encode("${file("${var.lega_conf}")}")}"
  cidr = "${var.cidr}"
}
module "frontend" {
  source = "./instances/frontend"
  private_ip = "192.168.10.15"
  ega_key = "${openstack_compute_keypair_v2.ega_key.name}"
  ega_net = "${openstack_networking_network_v2.ega_net.id}"
  lega_conf = "${base64encode("${file("${var.lega_conf}")}")}"
}
module "monitors" {
  source = "./instances/monitors"
  private_ip = "192.168.10.16"
  ega_key = "${openstack_compute_keypair_v2.ega_key.name}"
  ega_net = "${openstack_networking_network_v2.ega_net.id}"
  lega_conf = "${base64encode("${file("${var.lega_conf}")}")}"
}
module "vault" {
  source = "./instances/vault"
  volume_size = 300
  private_ip = "192.168.10.17"
  ega_key = "${openstack_compute_keypair_v2.ega_key.name}"
  ega_net = "${openstack_networking_network_v2.ega_net.id}"
  lega_conf = "${base64encode("${file("${var.lega_conf}")}")}"
}
module "workers" {
  source = "./instances/workers"
  count = 4
  private_ip_keys = "192.168.10.12"
  private_ips = ["192.168.10.100","192.168.10.101","192.168.10.102","192.168.10.103"]
  ega_key = "${openstack_compute_keypair_v2.ega_key.name}"
  ega_net = "${openstack_networking_network_v2.ega_net.id}"
  lega_conf = "${base64encode("${file("${var.lega_conf}")}")}"
  rsa_home = "${var.rsa_home}"
  gpg_home = "${var.gpg_home}"
  gpg_passphrase = "${var.gpg_passphrase}"
  gpg_certs = "${var.gpg_certs}"
}
