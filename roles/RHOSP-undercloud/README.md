Role Name
=========

The role sets the environment to install an undercloud and deploy an overcloud into a virtual infrastructure for Red Hat OpenStack Platform.

Requirements
------------

It's tested to work on a Red Hat Enterprise Linux version 8.4 system. Requires a virtual infrastructure, preferably created by the role RHOSP-virt-infra.

Role Variables
--------------

# TODO: Update

RHOSP_version: **17.0**|16.2|16.1|13.0
  This variable sets the version of RHOSP to install.

overcloud_ip: 10.0.0.254
  This variable sets the overcloud virtual IP (used for example to access Horizon)

dns_servers: ['8.8.8.8','8.8.4.4']
  List of servers to use as DNS.

ntp_servers: ['0.pool.ntp.org','1.pool.ntp.org','2.pool.ntp.org','3.pool.ntp.org']
  List of servers to use for NTP syncronization.

DefaultLeaf0: ...
  Default parameters to configure the default leaf 0

interfaces:
  Interfaces to use in each nic-configs template.

ComputeSriovProperties:
  isolcpus: '8-19'
  hugepagesz: '1GB'
  hugepages: 32
  kernelargs: 'iommu=pt intel_iommu=on'
  devmappings: 'sriov1:nic4,sriov2:nic5'
  sharedcpus: '4-7'
  hostmemory: 8192
  pcipassthrough:
    - vendor_id: 8086
      product_id: 1528
      address: '0000:85:00.0'
      network: 'sriov1'
    - vendor_id: 8086
      product_id: 1528
      address: '0000:85:00.1'
      network: 'sriov1'

  Default properties for ComputeSriov role

vms: []
  List of the virtual machines created, in the format:
```yaml
  - name: VM_NAME
    title: 'VM_TITLE'
    profile: 'undercloud'|'control'|'compute'
    memory: RAM_IN_KB
    vcpus: AMOUNT_OF_CPUS
    bmcport: VBMC_PORT_TO_ASSIGN
    mac: 'XX:XX:XX:XX:XX' (without the last octet)
    disk_size: DISK_SIZE_IN_KB
    backing_store: 'QCOW2_IMAGE' (image to use as base for the disk)
    cdrom: 'CDROM_IMAGE' (image to insert as cdrom, useful for cloud-init)
    nics:
      NETWORK_NAME_1: 'IP_ADDRESS_1'
      NETWORK_NAME_2: 'IP_ADDRESS_2'
      ...
```
  The role considers the defaults for RHOSP-virt-infra role:
    - undercloud
    - controller0
    - compute0

physical: []
  List of the physical machines to be connected to the lab, in the format:
```yaml
  - name: MACHINE_NAME
    title: 'MACHINE_TITLE'
    profile: 'control'|'compute'|'computesriov'
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

networks: []
  List of the virtual networks created. The role considers the defaults for RHOSP-virt-infra role:
    - RHOSPVirtLab_ctlplane
    - RHOSPVirtLab_external
    - RHOSPVirtLab_management

Dependencies
------------

- RHOSP-virt-infra (https://github.com/yampilop/RHOSPVirtLab/tree/rhel-hypervisor/roles/RHOSP-virt-infra)
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
    - vars/overcloud.yml
  gather_facts: no
  pre_tasks:
    - name: Wait for the undercloud to come up
      wait_for_connection:
        timeout: 120

    - name: Gathering facts
      setup:
  roles:
    - role: RHOSP-undercloud
```

License
-------

CC BY-SA 4.0

Author Information
------------------

Juan Pablo Martí (Technical Support Engineer) [jmarti@redhat.com][yampilop@gmail.com]
