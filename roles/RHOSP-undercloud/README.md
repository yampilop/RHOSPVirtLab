Role Name
=========

The role sets the environment to install an undercloud and deploy an overcloud into a virtual infrastructure for Red Hat OpenStack Platform.

Requirements
------------

It's tested to work on a Red Hat Enterprise Linux version 8.4 or 7.9 system. Requires a virtual infrastructure, preferably created by the role RHOSP-virt-infra.

Role Variables
--------------

RHOSP_version: **17.1**|17.0|16.2|16.1|13.0
  This variable sets the version of RHOSP to install.

RHOSP_release: **latest**|*valid_number*

CustomRhelImage: **"{{ RHOSP_version_supported[RHOSP_version].rhel_image.url }}"**|*"<url>"*|*"file://<full_path>"*
  Use this variable to customize the RHEL image to use as base for the undercloud and testing.
  You can use a URL ("http://...") or a path to a downloaded file ("file://<full_path>"). As you need to use the full path, the value will have a triple dash, for instance "file:///home/admin/rhel.qcow2"

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

vms:
  List of the virtual machines created, in the format:

```yaml
  - name: VM_NAME
    hypervisor: HYPERVISOR_NAME
    title: 'VM_TITLE'
    profile: 'PROFILE'
    memory: RAM_IN_KB
    vcpus: AMOUNT_OF_CPUS
    bmcport: VBMC_PORT_TO_ASSIGN
    mac: 'XX:XX:XX:XX:XX' (without the last octet)
    uefi: false
    disk_size: DISK_SIZE_IN_KB
    data_disk_size: DISK_SIZE_IN_KB
    backing_store: 'QCOW2_IMAGE' (image to use as base for the disk)
    cdrom: 'CDROM_IMAGE' (image to insert as cdrom, useful for cloud-init)
    nics:
      NETWORK_NAME_1: 'IP_ADDRESS_1'
      NETWORK_NAME_2: 'IP_ADDRESS_2'
      ...
```

  The role considers the defaults for RHOSP-virt-infra role:
    - undercloud
    - vcontroller0
    - vcompute0

  The profile value can be one of the listed in `overcloud_roles` variable with `virtual: True`.

physical:
  List of the physical machines to be connected to the lab, in the format:

```yaml
  - name: MACHINE_NAME
    leaf: LEAF_NAME
    title: 'MACHINE_TITLE'
    profile: 'PROFILE'
    memory: RAM_IN_KB
    cpus: AMOUNT_OF_CPUS
    pm_type: "ipmi"|"redfish"|"ilo"|"idrac"
    pm_user: "PM_USER_NAME"
    pm_password: "PM_PASSWORD"
    pm_addr: "PM_IP_ADDRESS"
    pm_port: "623"|"PM_PORT_IF_DIFFERENT_FROM_DEFAULT"
    mac: 'XX:XX:XX:XX:XX:XX' (full MAC address of the ctlplane interface)
    capabilities: 'LIST_OF_CAPABILITIES'
    disk_size: DISK_SIZE_IN_KB
    nics:
      nic1: 'ens1f0'
      nic2: 'ens1f1'
```

  The role considers no physical machines by default.

  The profile value can be one of the listed in `overcloud_roles` variable.

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
    - vars/vms.yml
    - vars/physical.yml
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

Juan Pablo Martí (Technical Support Engineer) [jmarti@redhat.com][yampilop@gmail.com]
