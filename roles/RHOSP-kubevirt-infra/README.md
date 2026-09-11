RHOSP-kubevirt-infra
=========

The role creates a KubeVirt-based virtual infrastructure (Kubernetes-native VMs) for Red Hat OpenStack Platform deployed in a Kubernetes cluster with KubeVirt.

Requirements
------------

Tested with Red Hat Enterprise Linux versions 7.9, 8.4, 9.6, or 10.2 (for the RHEL cloud image).

Infrastructure:
- Kubernetes cluster (OpenShift 4.10+) with KubeVirt installed
- oc/kubectl CLI access to the cluster with admin privileges
- RHOSP Undercloud deployed and running (via RHOSP-undercloud role)

RHEL Cloud Image:
- RHEL cloud image matching the RHOSP version (for VM base via CustomRhelImage parameter)

Role Variables
--------------

RHOSP_version: **17.1**|16.2
  This variable sets the version of RHOSP to install.

RHOSP_release: **latest**|*valid_number*

CustomRhelImage: **"{{ RHOSP_version_supported[RHOSP_version].rhel_image.url }}"**|*"<url>"*|*"file://<full_path>"*
  Customize the RHEL cloud image used as the base for KubeVirt VMs. Specify a URL ("http://...") or local file path ("file://<full_path>"). Use the full path with triple slash for local files, e.g., "file:///home/admin/rhel.qcow2"

CustomOcClientUrl: **"https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz"**|*"<url>"*
  Customize the OpenShift client (oc/kubectl) archive URL. Useful for air-gapped environments or to use a specific version. Specify a URL to a tar.gz archive containing oc and kubectl binaries.

cleanup: **False**|True
  Clean up KubeVirt resources (VirtualMachines, UserDefinedNetworks, Secrets) before creation.

create: **True**|False
  Create KubeVirt resources (VirtualMachines, UserDefinedNetworks, Secrets). Useful with cleanup:True to reset the environment.

leafs:
  **Single-site only:** KubeVirt deployments support only the default `overcloud` leaf.
  DCN (Distributed Cloud Node) configurations are **not supported**. The `leafs` list
  must contain only one entry named `overcloud`. This leaf defines the logical network
  model for the deployment:

  - `name` - Must be `"overcloud"` (single site only, no DCN).
  - `ctlplane_bridge` - KubeVirt network for provisioning: `{name}` (no `interface` needed).
  - `ctlplane_subnet` - The provisioning subnet: `name`, `cidr`, `dhcp_start`, `dhcp_end`,
    `inspection_iprange`, `gateway`, `vip` (control-plane VIP) and `masquerade`.
  - `additional_bridges` - Extra isolated networks (e.g., `br-external`): each `{name,
    ipv4.address}` (no `interface` trunking).
  - `networks` - List of isolated networks (Tenant, Storage, InternalApi, StorageMgmt,
    External, etc.). Each network has `name`, `bridge`, `vip` (boolean), `mtu`, and a
    `subnet` block with `ip_subnet`, `allocation_pools`, `vlan`, `gateway`, `vip`.

undercloud:
  The director host, defined separately from the overcloud `machines` list. This role
  only supports `type: kubevirt` (a VM this role creates). For libvirt or physical
  machines, use the RHOSP-virt-infra role. The dict is intentionally minimal - only the
  fields that actually vary are set. The role injects the constants that never change
  for the undercloud (name=undercloud, pre_provisioned=true, openstack.role=undercloud)
  so they cannot be set wrong. No `pm` block is used (it is the director and is not
  power-managed by the lab). When it is a kubevirt VM it is otherwise built like the
  overcloud VMs below (this role appends it to its internal `kubevirt_machines` view).
  Minimal example:

```yaml
undercloud:
  type: kubevirt
  # openstack:                 # optional
  #   local_interface: eth0    # control-plane NIC name (default eth0)
  #   management_interface: eth1  # Ansible access NIC (default eth1)
  kubevirt:
    title: 'VM_TITLE'
    cpus: AMOUNT_OF_CPUS
    memory: RAM_IN_GI
    disks:
    - root: true
      size: DISK_SIZE_IN_GI
    network:
      interfaces:
      - name: nic1
        mac: 'XX:XX:XX:XX:XX:XX'
        bridge: br-ctlplane
      # The mgmt/Ansible-access NIC is injected by the role; do not list it here.
```

  See `vars/machines.yml` for the full undercloud schema.

machines:
  List of the overcloud nodes. This role only manages `type: kubevirt` (VMs created by
  this role); for libvirt or physical machines use the RHOSP-virt-infra role. By default
  one virtual controller and one virtual compute. Every entry shares common top-level
  parameters and is tagged with a `type` discriminator; technology-specific parameters
  live in a block named after the type.

  A kubevirt VM (`type: kubevirt`):

```yaml
  - name: MACHINE_NAME
    type: kubevirt
    pre_provisioned: false     # optional: true = boot from RHEL base image + cloud-init
    openstack:
      role: PROFILE            # virtual-capable overcloud role
      ctlplane_ip: 192.168.24.121  # required when pre_provisioned (deployed server)
    # TODO: Power management (pm) not supported until KubeVirtBMC is implemented (https://github.com/kubevirtbmc/kubevirtbmc)
    #pm:
    #  type: ipmi
    #  user: BMC_USER
    #  password: BMC_PASSWORD
    #  address: localhost
    #  port: KUBEVIRTBMC_PORT
    #  mode: bios               # bios | uefi
    kubevirt:
      title: 'VM_TITLE'
      cpus: AMOUNT_OF_CPUS
      memory: RAM_IN_GI
      disks:                   # one or more; exactly one root
      - root: true
        size: DISK_SIZE_IN_GI
      - size: DATA_DISK_SIZE_IN_GI  # optional extra data disk(s)
      network:
        interfaces:
        - name: nic1
          mac: 'XX:XX:XX:XX:XX:XX'
          bridge: BRIDGE_NAME
        - name: mgmt           # optional: the Ansible access NIC - name must be `mgmt`
          mac: 'XX:XX:XX:XX:XX:XX'
          bridge: br-management  # its IP comes from the inventory `ansible_host`
```

  By default `machines` contains one virtual controller and one virtual compute, so the
  role creates those plus the `undercloud` VM.

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

  An interface **named `mgmt`** (the `management_interface_name`) marks the NIC that
  Ansible uses to reach the machine. Its IP is **not** stored in `machines.yml`; it is
  taken from the machine's `ansible_host` entry in the `inventory` file. Cloud-init
  applies that address statically at first boot and os-net-config later reuses it.

  **Pre-provisioning requirement:** All KubeVirt machines must use `pre_provisioned: true`.
  Ironic provisioning is not supported until KubeVirtBMC is implemented. The undercloud
  is always `pre_provisioned: true` (implicit). For a **pre_provisioned kubevirt VM** the
  role:
  - Backs the root disk with the RHEL base image (`<RHOSP_version>.rhel_image.name`)
  - Builds a per-machine cloud-init ISO (`<machine>-init.iso`) from user-data, meta-data,
    and network-config and attaches it to the VM

  The cloud-init login user is `stack` for the undercloud and the overcloud SSH user
  otherwise (`heat-admin` on 16.2, `tripleo-admin` on 17.1). The management interface
  (`mgmt` NIC) IP is seeded from the inventory `ansible_host` via network-config.
  For overcloud nodes, the ctlplane NIC is also configured with the static
  `openstack.ctlplane_ip` so the undercloud can reach it over SSH for deployed-server
  deployment.

  All overcloud nodes in `machines` must share the same `pre_provisioned` value (the
  undercloud is exempt). The role validates this and fails early otherwise.

Credentials (lab-only weak defaults; override in `vault_credentials.yaml`):

VmRootPassword: **redhat**
  Password for the `root` account in each KubeVirt VM (set via cloud-init).

VmStackPassword: **redhat**
  Password for the overcloud SSH user account in each KubeVirt VM (set via cloud-init).
  User name is `stack` for undercloud, `heat-admin` on 16.2, `tripleo-admin` on 17.1.

Note: Power management (BMC credentials) is not supported until KubeVirtBMC is implemented
(https://github.com/kubevirtbmc/kubevirtbmc).

Kubernetes Networking:
  Network configuration for KubeVirt VMs is managed through the Kubernetes cluster's
  networking plugins (e.g., Multus, OVN, SR-IOV). The `leafs` model in `vars/options.yml`
  defines the logical network topology; the role translates this into KubeVirt
  UserDefinedNetwork (UDN) resources that implement the actual connectivity.
  The undercloud accesses VMs via the cluster's service networking.

Example Playbook
----------------

```yaml
- name: Infrastructure configuration
  hosts: infrastructure
  vars_files:
    - vars/options.yml
    - vars/machines.yml
  pre_tasks:
    - name: Set ansible_user to the current user
      set_fact:
        ansible_user: "{{ lookup('env','USER') }}"
  roles:
    - role: RHOSP-kubevirt-infra
```

License
-------

CC BY-SA 4.0

Author Information
------------------

Juan Pablo Martí (Software Maintenance Engineer) [jmarti@redhat.com][yampilop@gmail.com]
