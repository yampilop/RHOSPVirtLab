RHOSP-virt-infra
=========

The role creates a virtual infrastructure for Red Hat OpenStack Platform.

Requirements
------------

It's tested to work on a Red Hat Enterprise Linux version 8.4 or 7.9 system.

Requires rhel-system-roles package installed.

Role Variables
--------------

RHOSP_version: **17.1**|16.2
  This variable sets the version of RHOSP to install.

RHOSP_release: **latest**|*valid_number*

CustomRhelImage: **"{{ RHOSP_version_supported[RHOSP_version].rhel_image.url }}"**|*"<url>"*|*"file://<full_path>"*
  Use this variable to customize the RHEL image to use as base for the undercloud and testing.
  You can use a URL ("http://...") or a path to a downloaded file ("file://<full_path>"). As you need to use the full path, the value will have a triple dash, for instance "file:///home/admin/rhel.qcow2"

cleanup: **False**|True
  This variable sets if the resources (domains, networks, storage) should be cleaned before the creation process.

create: **True**|False
  This variable sets if the resources (domains, networks, storage) should be created. Useful in combination with cleanup:True to wipe the lab environment.

external_if: eno1
  This variable sets the interface that connects the hypervisor with the Internet.

overcloud_ip: 10.0.0.254
  This variable sets the overcloud virtual IP (used for example to access Horizon)

forward_network: RHOSPVirtLab_external
  This variable sets the network the forwarded ports will be attached to.

forwarded_ports: [80,6080,5000]
  List of ports to be forwarded to the overcloud IP (enabling access to Horizon using the hypervisor IP address)

DefaultLeaf0:
  Default parameters to configure the default leaf 0.

DCNLeafs:
  Variable used to define leafs when making a DCN deployment.

undercloud:
  The director host, defined separately from the overcloud `machines` list. It is a
  single node tagged with a `type` discriminator: `libvirt` (a VM this role creates) or
  `physical` (a pre-existing, admin-prepared host this role does not create). The dict is
  intentionally minimal - only the fields that actually vary are set. The role injects the
  constants that never change for the undercloud (name=undercloud, pre_provisioned=true,
  openstack.role=undercloud) so they cannot be set wrong, and creates **no** virtualbmc for
  it (it is the director and is not power-managed by the lab, so no `pm` block is used;
  the domain boot mode defaults to bios - add `pm: {mode: uefi}` only for a uefi
  undercloud). When it is a libvirt VM it is otherwise built like the overcloud VMs below
  (this role appends it to its internal `libvirt_machines` view). Minimal example:

```yaml
undercloud:
  type: libvirt
  # openstack:                 # optional
  #   local_interface: eth0    # control-plane NIC name (default eth0)
  #   management_interface: eth1  # libvirt only, Ansible access NIC (default eth1)
  libvirt:
    title: 'VM_TITLE'
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
      - name: nic2
        mac: 'XX:XX:XX:XX:XX:XX'
        bridge: br-management
        management: true
```

  See `vars/machines.yml` for the full undercloud schema, and the **Physical undercloud**
  note below for the `type: physical` case.

machines:
  List of the overcloud nodes (both libvirt VMs and physical baremetal nodes). By default
  one virtual controller and one virtual compute. Every entry shares common top-level
  parameters and is tagged with a `type` discriminator; technology-specific parameters
  live in a block named after the type.

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
      address: localhost       # localhost/hypervisor for VMs
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
        interfaces:            # each NIC attaches to a hypervisor bridge (type=bridge)
        - name: nic1
          mac: 'XX:XX:XX:XX:XX:XX'
          bridge: BRIDGE_NAME
        - name: nic2
          mac: 'XX:XX:XX:XX:XX:XX'
          bridge: BRIDGE_NAME
          management: true     # optional: marks the Ansible access NIC (IP from inventory)
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
      mac: 'XX:XX:XX:XX:XX:XX'  # boot NIC MAC (for introspection)
      nics:
        nic1: 'ens1f0'
        nic2: 'ens1f1'
```

  By default `machines` contains one virtual controller and one virtual compute, so the
  role creates those plus the `undercloud` VM (the defaults ship a commented example for
  physical nodes).

  The `openstack.role` value can be one of the following:
    - controller
    - compute
    - computeovsdpdk
    - computeovsdpdksriov
    - computesriov
    - computeovshwoffload
    - cephstorage
    - computehci

  VMs may only use virtual-capable profiles (those with `virtual: True` in the
  `overcloud_roles` variable from `roles/RHOSP-undercloud/vars/main.yml`).

  The `management: true` interface flag marks the NIC that Ansible uses to reach the
  machine. Its IP is **not** stored in `machines.yml`; it is taken from the machine's
  `ansible_host` entry in the `inventory` file. For a libvirt undercloud, cloud-init
  applies that address statically at first boot and os-net-config later reuses it; for
  a physical undercloud the address is simply reachable via the inventory.

  **Physical undercloud.** The undercloud may be `type: physical` instead of a libvirt
  VM. Such a host is assumed to be *admin-prepared*: RHEL installed, the `stack` user
  present with the hypervisor's SSH public key authorized, and its NICs already up (the
  control-plane NIC on the ctlplane L2, plus a management/access IP matching its
  inventory `ansible_host`). This role does **not** create it, start a domain for it,
  wait on cloud-init, or reconfigure its interfaces; it only adds an `/etc/hosts` entry
  so the `stack@undercloud` alias resolves. Set `openstack.local_interface` (default
  `eth0`) to the real control-plane device name; `openstack.management_interface`
  (default `eth1`) applies only to a libvirt undercloud.

  The `pre_provisioned` flag (top level, both types) records whether the node already
  has an OS loaded ("deployed server") or will be provisioned later by ironic
  (unprovisioned, the default). The undercloud is always `pre_provisioned: true`; the
  other machines default to unprovisioned but can opt in. For a **pre_provisioned
  libvirt VM** the role:
  - backs the root disk with the RHEL base image (`<RHOSP_version>.rhel_image.name`)
    and populates it with `virt-resize`, and
  - builds a per-machine NoCloud (cidata) ISO — `<machine>-init.iso` — from user-data /
    meta-data / network-config and attaches it as a SATA cdrom.

  The cloud-init login user is `stack` for the undercloud role and the overcloud SSH
  user otherwise (`heat-admin` on 16.2, `tripleo-admin` on 17.1). When the machine has a
  `management: true` interface, its inventory `ansible_host` is seeded via network-config.
  For a **pre_provisioned overcloud** node cloud-init also seeds the node's ctlplane NIC
  with the static `openstack.ctlplane_ip` (defaulting the route to the ctlplane network
  address) so the undercloud can reach it over SSH; the injected public key is the
  hypervisor's, so the undercloud (carrying the matching private key) can drive the
  deployed-server deployment. An **unprovisioned** VM gets empty disks and no cloud-init
  cdrom.

  Pre-provisioned (deployed-server) and ironic-provisioned overcloud nodes cannot be
  mixed: every overcloud node in `machines` must share the same `pre_provisioned` value
  (the undercloud is defined separately and is exempt). The role validates this and
  fails early otherwise. This is currently a global check; a future leaf refactor
  (making `openstack.leaf` the single leaf identifier for both VMs and physical nodes)
  will make it per-leaf, so a leaf rather than the whole deployment is the unit that
  cannot mix.

  Convenience views `libvirt_machines` and `physical_machines` (defined in the role
  `vars/main.yml`) filter this list by `type`. Because this role builds the undercloud,
  a libvirt undercloud is appended to `libvirt_machines`; a physical undercloud is
  admin-prepared and never appears in either view.

  **When libvirt / VirtualBMC work is skipped.** The role only touches the parts of the
  hypervisor a given lab actually needs, driven by two derived flags in `vars/main.yml`:

  - `libvirt_required` (`libvirt_machines | length > 0`) - there is at least one VM to
    build (a libvirt undercloud and/or libvirt overcloud nodes). When it is **false** (a
    *physical* undercloud **and** no libvirt machines), the role installs no libvirt
    packages, does not enable the libvirt services, join the libvirt/kvm groups, or
    create any libvirt networks/storage/domains, and **skips the nested-virtualization
    checks** (no KVM-module probe and no "please reboot" prompt). Only the host-level
    plumbing still runs: network bridges, firewall, and SSH access to the undercloud.
  - `vbmc_required` (`machines | selectattr('type','equalto','libvirt') | length > 0`) -
    there is at least one libvirt **overcloud** node. VirtualBMC only emulates a BMC so
    ironic can power-cycle a VM, so the undercloud (the director, no `pm`, never
    power-managed) is deliberately excluded. When it is **false**, the role installs and
    configures no VirtualBMC at all - so a lab with a libvirt undercloud but no libvirt
    overcloud VMs still builds the undercloud VM but sets up no vbmc.

  `netaddr` (for the `ipaddr` filters that build the host bridges and render the network
  config) is installed independently of both flags, since it is needed even for a fully
  physical lab.

networks:
  List of the virtual networks created. The default values are:
    - RHOSPVirtLab_ctlplane
    - RHOSPVirtLab_external
    - RHOSPVirtLab_management

  If you will add physical nodes, you need to define `hypervisor_if: {{ifname}}` parameter on `RHOSPVirtLab_ctlplane` and `RHOSPVirtLab_external` networks, setting the interfaces that will be attached to the bridges. Make sure those interfaces are configured as trunks with a native vlan in the switch.

Example Playbook
----------------

```yaml
- name: Infrastructure configuration
  hosts: infrastructure
  vars_files:
    - vars/options.yml
    - vars/machines.yml
    - vars/networks.yml
  pre_tasks:
    - name: Set ansible_user to the current user
      set_fact:
        ansible_user: "{{ lookup('env','USER') }}"
  roles:
    - role: RHOSP-virt-infra
```

License
-------

CC BY-SA 4.0

Author Information
------------------

Juan Pablo Martí (Software Maintenance Engineer) [jmarti@redhat.com][yampilop@gmail.com]
