Role Name
=========

The role sets the environment to install an undercloud and deploy an overcloud into a virtual infrastructure for Red Hat OpenStack Platform.

Requirements
------------

It's tested to work on a Red Hat Enterprise Linux version 8.4 or 7.9 system. Requires a virtual infrastructure, preferably created by the role RHOSP-virt-infra.

Role Variables
--------------

RHOSP_version: **17.1**|16.2
  This variable sets the version of RHOSP to install.

RHOSP_release: **latest**|*valid_number*

CustomRhelImage: **"{{ RHOSP_version_supported[RHOSP_version].rhel_image.url }}"**|*"<url>"*|*"file://<full_path>"*
  Use this variable to customize the RHEL image to use as base for the undercloud and testing.
  You can use a URL ("http://...") or a path to a downloaded file ("file://<full_path>"). As you need to use the full path, the value will have a triple dash, for instance "file:///home/admin/rhel.qcow2"

CustomCirrOSImage: **"{{ CirrOSDownloadLink }}"**|*"<url>"*|*"file://<full_path>"*
  Use this variable to customize the CirrOS image to use for testing.
  You can use a URL ("http://...") or a path to a downloaded file ("file://<full_path>"). As you need to use the full path, the value will have a triple dash, for instance "file:///home/admin/cirros.qcow2"

create: **True**|False
  This variable sets if the resources will be created or not. Useful in combination with cleanup:True to wipe the lab environment.

dns_servers: ['8.8.8.8','8.8.4.4']
  List of servers to use as DNS.

ntp_servers: ['0.pool.ntp.org','1.pool.ntp.org','2.pool.ntp.org','3.pool.ntp.org']
  List of servers to use for NTP syncronization.

forwarded_ports: **[80, 6080, 5000]**
  TCP ports the undercloud forwards (DNAT) to the overcloud public IP. Only applied
  when the control-plane leaf's `ctlplane_subnet.masquerade` is `true`: `post_deployment.sh`
  installs a small systemd oneshot (`rhospvirtlab-portforward.service`) that adds
  `iptables` DNAT rules for each port to the overcloud public IP, so the overcloud is
  reachable through the undercloud. The undercloud's ctlplane masquerade (SNAT) provides
  the return path, which is why the rules are only created when masquerade is enabled.
  This mirrors the hypervisor-side forwarding in the RHOSP-virt-infra role.

leafs:
  Ordered list of the deployment's leafs (L2 segments / routed subnets). The first entry
  is always the default control-plane leaf and must be named `overcloud`; any further
  entries are DCN (edge) leafs. Each role derives two views in its `vars/main.yml`:
  `default_leaf` (the `overcloud` leaf) and `dcn_leafs` (the rest). A single-site lab has
  just the one `overcloud` leaf; add entries for a DCN/spine-leaf deployment. Each leaf
  has:

  - `name` - leaf identifier (`overcloud` for the control-plane leaf).
  - `hypervisor` - the host whose bridges carry this leaf's L2.
  - `ctlplane_bridge` - `{name, interface}` for the control-plane bridge on the
    hypervisor. Set `interface` to trunk a real NIC into the bridge (needed for physical
    nodes); leave it `null` for a VM-only bridge.
  - `ctlplane_subnet` - the provisioning subnet: `name`, `cidr`, `dhcp_start`,
    `dhcp_end`, `inspection_iprange`, `gateway`, `vip` (the control-plane VIP) and
    `masquerade`. When `masquerade` is `true` on the control-plane leaf, the undercloud
    also forwards the `forwarded_ports` to the overcloud public IP (see `forwarded_ports`).
  - `additional_bridges` - extra bridges (e.g. `br-external`), each `{name, interface,
    ipv4.address}`.
  - `networks` - the isolated networks carried on this leaf (Tenant, Storage,
    InternalApi, StorageMgmt, External, ...). Each network has `name`, `bridge`, `vip`
    (boolean: whether the network gets a VIP), `mtu` and a `subnet` block (`ip_subnet`,
    `allocation_pools`, `vlan`, `gateway`, `vip`). `subnet.vip` is the concrete VIP
    address pinned in `vip_data.yaml`; the External network VIP - or the control-plane
    VIP when External is not defined - is also used as the overcloud's public IP.

  A DCN (edge) leaf is a second entry with its own hypervisor, subnets and networks, e.g.:

```yaml
leafs:
- name: overcloud            # control-plane leaf (as shipped)
  ...
- name: leaf1                # DCN leaf
  hypervisor: <hypervisor_name>
  additional_bridges:
  - name: br-external
    interface: null
    ipv4:
      address: 10.1.0.254
  ctlplane_bridge:
    name: br-ctlplane
    interface: null
  ctlplane_subnet:
    name: leaf1-subnet
    cidr: 192.168.25.0/24
    dhcp_start: 192.168.25.5
    dhcp_end: 192.168.25.99
    inspection_iprange: 192.168.25.100,192.168.25.120
    gateway: 192.168.25.254
    masquerade: false
  networks:                  # same shape as the overcloud leaf, on the leaf's subnets
  - name: Tenant
    bridge: br-ctlplane
    vip: false
    mtu: 1500
    subnet:
      ip_subnet: 172.17.0.0/24
      allocation_pools:
      - start: 172.17.0.5
        end: 172.17.0.99
      vlan: 10
  - name: Storage
    bridge: br-ctlplane
    vip: true
    mtu: 1500
    subnet:
      ip_subnet: 172.17.1.0/24
      allocation_pools:
      - start: 172.17.1.5
        end: 172.17.1.99
      vlan: 11
  - name: InternalApi
    bridge: br-ctlplane
    vip: true
    mtu: 1500
    subnet:
      ip_subnet: 172.17.2.0/24
      allocation_pools:
      - start: 172.17.2.5
        end: 172.17.2.99
      vlan: 12
  - name: StorageMgmt
    bridge: br-ctlplane
    vip: true
    mtu: 1500
    subnet:
      ip_subnet: 172.17.3.0/24
      allocation_pools:
      - start: 172.17.3.5
        end: 172.17.3.99
      vlan: 13
  - name: External
    bridge: br-external
    vip: true
    mtu: 1500
    subnet:
      ip_subnet: 10.1.0.0/24
      allocation_pools:
      - start: 10.1.0.5
        end: 10.1.0.99
      gateway: 10.1.0.254
```

RoleBridgeMappings:
  Per-role bridge/NIC layout rendered into each node's nic-config template (replaces the
  old flat `interfaces` list). A dict keyed by overcloud role name; a role not listed
  falls back to the `Default` entry. Each value is an ordered list of bridge definitions:

  - `type` - `ovs_bridge` | `linux_bridge` | `ovs_user_bridge` | `sriov_pf`.
  - `name` - the bridge (or PF) name.
  - `members` - devices on the bridge, in order (the first plain interface supplies the
    bridge MAC). A bare `nicN` is a plain interface; `nicNvM` is VF M of `nicN`; a dict
    is a nested device (`ovs_dpdk_bond` / `ovs_dpdk_port`).
  - `native` - the untagged network whose IP sits on the bridge itself. `CtlPlane` gets
    the control-plane IP + DNS + default route; a network name gets that network's IP
    (External also gets the default route); omit for an address-less bridge (e.g. a DPDK
    user bridge).
  - `vlans` - tagged networks carried as VLAN sub-interfaces, auto-filtered to the
    networks the role actually carries (so the same list is safe to reuse across roles).

  A `sriov_pf` entry also takes `numvfs` and an optional `link_mode: switchdev` (for
  hardware offload).

  Common archetypes (add a role key with a list like these; unlisted roles use `Default`):

```yaml
# Controller - only the control plane on br-ex
Controller:
- {type: ovs_bridge, name: br-ex, members: [nic1], native: CtlPlane, vlans: []}

# Compute - single-nic-vlans (External also tagged on the same bridge)
Compute:
- type: ovs_bridge
  name: br-ex
  members: [nic1]
  native: CtlPlane
  vlans: [Tenant, Storage, InternalApi, StorageMgmt, External]

# ComputeSriov - dedicated SR-IOV PF; VF 0 backs the External bridge
ComputeSriov:
- {type: ovs_bridge, name: br-vlans, members: [nic1], native: CtlPlane, vlans: [Tenant, Storage, InternalApi, StorageMgmt]}
- {type: ovs_bridge, name: br-ex, members: [nic2v0], native: External, vlans: []}   # nic2v0 = VF 0 of nic2
- {type: sriov_pf, name: nic2, numvfs: 8}

# ComputeOvsHwOffload - as SR-IOV, but the PF in switchdev mode
ComputeOvsHwOffload:
- {type: ovs_bridge, name: br-vlans, members: [nic1], native: CtlPlane, vlans: [Tenant, Storage, InternalApi, StorageMgmt]}
- {type: ovs_bridge, name: br-ex, members: [nic2v0], native: External, vlans: []}
- {type: sriov_pf, name: nic2, numvfs: 8, link_mode: switchdev}

# ComputeOvsDpdk - control/External on linux bridges, DPDK bond on an OVS user bridge
ComputeOvsDpdk:
- {type: linux_bridge, name: br-vlans, members: [nic1], native: CtlPlane, vlans: [Tenant, Storage, InternalApi, StorageMgmt]}
- {type: linux_bridge, name: br-ex, members: [nic2], native: External, vlans: []}
- type: ovs_user_bridge
  name: br-dpdk
  members:
  - type: ovs_dpdk_bond
    name: dpdkbond0
    members:
    - {type: ovs_dpdk_port, name: dpdk0, driver: vfio-pci, members: [nic3]}
    - {type: ovs_dpdk_port, name: dpdk1, driver: vfio-pci, members: [nic4]}

# ComputeOvsDpdkSriov - a DPDK bond built on SR-IOV VFs of the same PF (nic2)
ComputeOvsDpdkSriov:
- {type: linux_bridge, name: br-vlans, members: [nic1], native: CtlPlane, vlans: [Tenant, Storage, InternalApi, StorageMgmt]}
- {type: linux_bridge, name: br-ex, members: [nic2v0], native: External, vlans: []}
- {type: sriov_pf, name: nic2, numvfs: 8}
- type: ovs_user_bridge
  name: br-dpdk
  members:
  - type: ovs_dpdk_bond
    name: dpdkbond0
    members:
    - {type: ovs_dpdk_port, name: dpdk0, driver: vfio-pci, members: [nic2v1]}
    - {type: ovs_dpdk_port, name: dpdk1, driver: vfio-pci, members: [nic2v2]}
```

ComputeSriovProperties, ComputeOvsHwOffloadProperties, ComputeOvsDpdkProperties, ComputeOvsDpdkSriovProperties:
  Default properties for NFV roles

CephStorageProperties:
  Default properties for Ceph roles.

DeployOctavia: **False** | True
  This variable sets if the LBaaS Octavia service will be deployed.

DeployDesignate: **False** | True
  This variable sets if the DNSaaS Designate service will be deployed (only available for RHOSP_version >= 17).

DeployFrr: **False** | True
  This variable sets if the FRRouting service will be deployed (only available for RHOSP_version >= 17.1).

RegisterNodes: **False** | True
  This variable sets if the nodes will be registered.

NeutronDriver: **ovn** | ovs
  This variable sets the neutron driver to use.

DisableTelemetry: **True** | False
  This variable allows to disable telemetry. Set to False if you want to use Telemetry parameter.

Telemetry: **False** | { MetricsConnectorHost: default-interconnect-5671-service-telemetry.apps.ocp-sno-for-stf.redhat.local, MetricsConnectorIPAddress: 10.8.223.249, Cloud: cloud1 }
  Variable used to define telemetry parameters.

LowMemUsage: **True** | False
  Adds the low-memory-usage environment to the default leaf deploy to reduce the services' memory footprint.

ControllersFencing: **True** | False
  Enables STONITH fencing for the controllers (also forced on when a ComputeInstanceHA role is present).

BridgeMappings: **'datacentre:br-ex'**
  Default Neutron bridge_mappings applied to the compute nodes.

NetworkVlanRanges: **'datacentre:1:1000'**
  Neutron network VLAN ranges for the `datacentre` physical network.

SnmpdReadonlyUserPassword: **RHOSPVirtLab**
  Password for the read-only snmpd user configured on the undercloud and overcloud.

UndercloudFullUpdate: **True** | False
  Runs a full `yum update` of the undercloud host on every run (reboots if needed). Set to False for faster, more predictable runs.

UndercloudExtraFirewallRules: **[]** | *dict of rules*
  Extra firewalld rules to open on the undercloud, keyed by rule name (see the commented example in `vars/options.yml`).

vncproxy: **''**
  Nova VNC proxy host set on the overcloud; leave empty for the default, or set the public/VIP address to enable noVNC console access.

Credentials (lab-only weak defaults; override in `vault_credentials.yaml`):

BmcUsername / BmcPassword: **admin** / **admin**
  Credentials for the VirtualBMC endpoints and physical-node BMC/IPMI access.

OvercloudAdminPassword: **redhat**
  The overcloud Keystone `admin` password.

OvercloudAdminEmail: **admin@example.com**
  The overcloud `admin` account email.

TestUserPassword: **redhat**
  Password for the test `admin` user created by `overcloud_resources.yaml`.

undercloud:
  The director host, defined separately from the overcloud `machines` list and shared
  with the RHOSP-virt-infra role. It is a single node tagged with a `type` discriminator
  (`libvirt` for a VM the lab creates, `physical` for a pre-existing admin-prepared
  host). The dict is intentionally minimal - only the fields that actually vary are set.
  The roles inject the constants that never change for the undercloud (name=undercloud,
  pre_provisioned=true, openstack.role=undercloud) so they cannot be set wrong, and
  create **no** virtualbmc for it (it is the director and is not power-managed by the lab,
  so no `pm` block is used; the domain boot mode defaults to bios - add `pm: {mode: uefi}`
  only for a uefi undercloud). By default it is a libvirt VM:

```yaml
  undercloud:
    type: libvirt
    # openstack:                   # optional
    #   local_interface: eth0      # control-plane NIC (-> undercloud.conf), default eth0
    #   management_interface: eth1 # libvirt only, Ansible-access NIC, default eth1
    libvirt:
      title: 'Undercloud'
      hypervisor: HYPERVISOR_NAME
      cpus: AMOUNT_OF_CPUS
      memory: RAM_IN_KIB
      disks:
      - root: true
        size: DISK_SIZE_IN_BYTES
      network:
        interfaces:
        - name: nic1
          mac: 'XX:XX:XX:XX:XX:XX'
          bridge: br-ctlplane
        # The mgmt/Ansible-access NIC (named `mgmt`, IP from inventory ansible_host) is
        # injected by the RHOSP-virt-infra role; do not list it here.
```

  The undercloud may instead be `type: physical`. A physical undercloud is treated as
  *admin-prepared* (RHEL installed, `stack` user with the hypervisor's SSH key, NICs
  already up); this role skips the cloud-init wait and does not reconfigure its
  management interface — it only runs subscription/repos/packages, writes
  `undercloud.conf` and deploys. Set `openstack.local_interface` to the real
  control-plane device name (default `eth0`); no `pm` block is needed (it is not
  power-managed by the lab). See `vars/machines.yml` for the full schema.

machines:
  List of the overcloud nodes (both libvirt VMs and physical baremetal nodes), shared
  with the RHOSP-virt-infra role. By default one virtual controller and one virtual
  compute. Every entry shares common top-level parameters and is tagged with a `type`
  discriminator; technology-specific parameters live in a block named after the type.

  A libvirt VM (`type: libvirt`):

```yaml
  - name: MACHINE_NAME
    type: libvirt
    pre_provisioned: false     # optional: true = boot from RHEL base image + cloud-init
    openstack:
      role: PROFILE            # virtual-capable overcloud role
      ctlplane_ip: 192.168.24.121  # required when pre_provisioned (deployed server)
    pm:
      type: ipmi
      user: BMC_USER
      password: BMC_PASSWORD
      address: localhost
      port: VBMC_PORT          # virtualbmc port (unique per VM)
      mode: bios               # bios | uefi
    libvirt:
      title: 'VM_TITLE'
      hypervisor: HYPERVISOR_NAME
      cpus: AMOUNT_OF_CPUS
      memory: RAM_IN_KIB
      disks:                   # one or more; exactly one root; all attached as virtio
      - root: true
        size: DISK_SIZE_IN_BYTES
      - size: DATA_DISK_SIZE_IN_BYTES  # optional extra data disk(s)
      network:
        interfaces:
        - name: nic1
          mac: 'XX:XX:XX:XX:XX:XX'
          bridge: BRIDGE_NAME
```

  A physical baremetal node (`type: physical`):

```yaml
  - name: MACHINE_NAME
    type: physical
    pre_provisioned: false     # optional: true = OS already loaded (deployed server)
    openstack:
      role: PROFILE
      leaf: LEAF_NAME
      ctlplane_ip: 192.168.24.131  # required when pre_provisioned (deployed server)
    pm:
      type: "ipmi"|"redfish"|"ilo"|"idrac"
      user: "PM_USER_NAME"
      password: "PM_PASSWORD"
      address: "PM_IP_ADDRESS"
      port: "623"
      mode: bios               # bios | uefi
    physical:
      cpus: AMOUNT_OF_CPUS
      memory: RAM_IN_KIB
      disk: DISK_SIZE_IN_BYTES
      mac: 'XX:XX:XX:XX:XX:XX'
      nics:
        nic1: 'ens1f0'
        nic2: 'ens1f1'
```

  By default `machines` contains one virtual controller and one virtual compute; the
  RHOSP-virt-infra role defaults ship a commented physical-node example.

  The `openstack.role` value can be one of those listed in the `overcloud_roles`
  variable; VMs may only use profiles with `virtual: True`. Convenience views
  `libvirt_machines` and `physical_machines` (defined in the role `vars/main.yml`)
  filter this list by `type`; the undercloud is defined separately and is not part of
  them.

  The `pre_provisioned` flag (top level, both types) marks a node whose OS is already
  loaded ("deployed server") versus one provisioned later by ironic (the default). A
  pre_provisioned libvirt VM is booted from the RHEL base image with a cloud-init cdrom
  (see the RHOSP-virt-infra role for details); the cloud-init user is the overcloud SSH
  user (`heat-admin` on 16.2, `tripleo-admin` on 17.1).

  When overcloud nodes are `pre_provisioned` the role drives a TripleO **deployed-server**
  deployment for that leaf instead of the ironic flow: node import/introspection are
  skipped, each node keeps the static `openstack.ctlplane_ip` cloud-init assigned to its
  ctlplane NIC, and the deploy is authored accordingly. On 16.2 this generates a
  `DeployedServerPortMap` + `HostnameMap` (`deployed-server-ports.yaml`) alongside the
  upstream `deployed-server-environment.yaml`; on 17.1 `openstack overcloud node provision`
  is run with `managed: false` (per-node ctlplane `fixed_ip`) to emit
  `overcloud-baremetal-deployed.yaml`. The deploy runs with `--disable-validations`.
  Pre-provisioned and ironic-provisioned overcloud nodes cannot be mixed: every overcloud
  node must share the same `pre_provisioned` value (validated by the RHOSP-virt-infra role,
  which fails early otherwise). This is a global check for now; a future leaf refactor will
  make it per-leaf.

  A `pre_provisioned` node must **not** define a `pm` block: ironic does not power-manage
  deployed servers, so a BMC is meaningless there. The one exception is when
  `ControllersFencing` is enabled - controllers then keep a `pm`/BMC for STONITH fencing -
  in which case the `pm` block is allowed. The role validates this and fails early if a
  pre_provisioned node carries a `pm` block while `ControllersFencing` is off.

Networks:
  There is no longer a standalone `networks` variable. The isolated networks (Tenant,
  Storage, InternalApi, StorageMgmt, External, ...) are defined per leaf under
  `leafs[].networks`, and the underlying libvirt networks/bridges are assembled by the
  RHOSP-virt-infra role from the `leafs` model (plus the management NAT network) into a
  derived `libvirt_networks` list. Each leaf's `ctlplane_bridge` and `additional_bridges`
  become the lab's L2 bridges, named `RHOSPVirtLab_<bridge-without-br->` (e.g.
  `br-ctlplane` -> `RHOSPVirtLab_ctlplane`).

  To add physical nodes, trunk a real hypervisor NIC into a bridge by setting
  `interface: <ifname>` on that leaf's `ctlplane_bridge` (and/or an `additional_bridges`
  entry) instead of leaving it `null`. Make sure those interfaces are configured as
  trunks with a native VLAN on the switch.

Dependencies
------------

- RHOSP-virt-infra (https://github.com/yampilop/RHOSPVirtLab/tree/master/roles/RHOSP-virt-infra)
- geerlingguy.swap

Example Playbook
----------------

```yaml
- name: Openstack configuration
  hosts: openstack
  vars_files:
    - vault_credentials.yaml
    - vars/options.yml
    - vars/machines.yml
  gather_facts: no

  pre_tasks:
    - name: Wait for the undercloud to come up
      wait_for_connection:
        timeout: 120
      when: create | bool

    - name: Gathering facts
      setup:
      when: create | bool

  roles:
    - role: RHOSP-undercloud
      when: create | bool
```

License
-------

CC BY-SA 4.0

Author Information
------------------

Juan Pablo Martí (Software Maintenance Engineer) [jmarti@redhat.com][yampilop@gmail.com]
