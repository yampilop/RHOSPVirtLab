RHOSP-virt-infra
=========

The role creates a virtual infrastructure for Red Hat OpenStack Platform.

Requirements
------------

It's tested to work on a Red Hat Enterprise Linux version 8.4 or 7.9 system.

Requires rhel-system-roles package installed.

Role Variables
--------------

RHOSP_version: **17.1**|17.0|16.2|16.1|13.0
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

  By default the role creates:
    - undercloud
    - vcontroller0
    - vcompute0

  The profile value can be one of the following:
    - vcontroller
    - vcompute
    - vcephstorage
    - vcomputehci

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
```

  The role considers no physical machines by default.

  The profile value can be one of the following:
    - controller
    - compute
    - computeovsdpdk
    - computeovsdpdksriov
    - computesriov
    - computeovshwoffload
    - cephstorage
    - computehci

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
    - vars/vms.yml
    - vars/networks.yml
    - vars/overcloud.yml
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

Juan Pablo Martí (Technical Support Engineer) [jmarti@redhat.com][yampilop@gmail.com]
