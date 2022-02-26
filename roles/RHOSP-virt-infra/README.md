RHOSP-virt-infra
=========

The role creates a virtual infrastructure for Red Hat OpenStack Platform.

Requirements
------------

It's tested to work on a Red Hat Enterprise Linux version 8.4 system.

Role Variables
--------------

cleanup: **False**|True
  This variable sets if the resources (domains, networks, storage) should be cleaned before the creation process.

create: **True**|False
  This variable sets if the resources (domains, networks, storage) should be created. Useful in combination with cleanup:True to wipe the lab environment.

vms: []
  List of the virtual machines to be created, in the format:
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

networks: []
  List of the virtual networks to be created. The default values should work. You can replace or add the hypervisor_if values to set wich interfaces in the hypervisor are linked to each bridge (useful to connect physical nodes to the lab).
```yaml
networks:
  - name: RHOSPVirtLab_ctlplane
    bridge: br-ctlplane
    forward: false
    mac_suffix: '00'
    ipv4: false
    hypervisor_if: eno2
  - name: RHOSPVirtLab_storage
    bridge: br-storage
    forward: false
    mac_suffix: '01'
    ipv4: false
  - name: RHOSPVirtLab_storage_mgmt
    bridge: br-storage-mgmt
    forward: false
    mac_suffix: '02'
    ipv4: false
  - name: RHOSPVirtLab_internal_api
    bridge: br-internal-api
    forward: false
    mac_suffix: '03'
    ipv4: false
  - name: RHOSPVirtLab_tenant
    bridge: br-tenant
    forward: false
    mac_suffix: '04'
    ipv4: false
  - name: RHOSPVirtLab_external
    bridge: br-external
    forward: route
    mac_suffix: '05'
    ipv4:
      address: '10.0.0.1'
      netmask: '255.255.255.0'
      dhcp: false
  - name: RHOSPVirtLab_management
    bridge: br-management
    forward: nat
    mac_suffix: '0f'
    ipv4:
      address: '192.168.250.1'
      netmask: '255.255.255.0'
      dhcp:
        start: '192.168.250.100'
        end: '192.168.250.254'
        hosts: true
```

Example Playbook
----------------

```yaml
- name: Infrastructure configuration
  hosts: infrastructure
  vars_files:
    - vars/vms.yml
    - vars/networks.yml
  become: no
  roles:
    - role: RHOSP-virt-infra
      vars:
        cleanup: False
        create: True
```

License
-------

CC BY-SA 4.0

Author Information
------------------

Juan Pablo Martí (Technical Support Engineer) [jmarti@redhat.com][yampilop@gmail.com]
