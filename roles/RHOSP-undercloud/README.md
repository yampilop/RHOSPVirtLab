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

overcloud_ip: 10.0.0.254
  This variable sets the overcloud virtual IP (used for example to access Horizon)

dns_servers: ['8.8.8.8','8.8.4.4']
  List of servers to use as DNS.

ntp_servers: ['0.pool.ntp.org','1.pool.ntp.org','2.pool.ntp.org','3.pool.ntp.org']
  List of servers to use for NTP syncronization.

DefaultLeaf0:
  Default parameters to configure the default leaf 0.

interfaces:
  Interfaces to use in each nic-configs template.

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

DCNLeafs:
  Variable used to define leafs when making a DCN deployment.

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
        - name: nic2
          mac: 'XX:XX:XX:XX:XX:XX'
          bridge: br-management
          management: true         # Ansible access NIC (IP from inventory ansible_host)
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
  `overcloud-baremetal-deployed.yaml`. The deploy runs with `--disable-validations` and
  `--overcloud-ssh-user`/`--overcloud-ssh-key` pointing at the hypervisor deploy key
  copied to the undercloud. Pre-provisioned and ironic-provisioned overcloud nodes cannot
  be mixed: every overcloud node must share the same `pre_provisioned` value (validated by
  the RHOSP-virt-infra role, which fails early otherwise). This is a global check for now;
  a future leaf refactor will make it per-leaf.

networks:
  List of the virtual networks created. The role considers the defaults for RHOSP-virt-infra role:
    - RHOSPVirtLab_ctlplane
    - RHOSPVirtLab_external
    - RHOSPVirtLab_management

  If you will add physical nodes, you need to define `hypervisor_if: {{ifname}}` parameter on `RHOSPVirtLab_ctlplane` and `RHOSPVirtLab_external` networks, setting the interfaces that will be attached to the bridges. Make sure those interfaces are configured as trunks with a native vlan in the switch.

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
    - vars/networks.yml
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
