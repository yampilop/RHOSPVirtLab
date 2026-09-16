#!/usr/bin/env python3
"""
Migrate old var format (vms.yml, physical.yml, networks.yml) to new format (machines.yml).

Usage:
    python3 migrate-vars-to-new-format.py <path_to_old_vars_dir> <path_to_new_vars_dir>

Example:
    python3 scripts/migrate-vars-to-new-format.py ~/old-vars vars/

This script reads the old configuration files and generates:
  - vars/machines.yml (undercloud + machines with libvirt/physical/kubevirt blocks)
  - vars/options.yml (updated with merged leafs/networks configuration)
"""

import sys
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any
from io import StringIO


def load_yaml(filepath: str) -> Dict[str, Any]:
    """Load YAML file safely."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}


def update_options_file(filepath: str, custom_options: Dict[str, Any], leafs: Any = None) -> None:
    """Update vars/options.yml with migrated options by parsing and updating the dict."""
    # Parse existing YAML
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    # Update with custom options
    for key, value in custom_options.items():
        data[key] = value

    # Update leafs if provided
    if leafs is not None:
        data['leafs'] = leafs

    # Write back the updated file
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)


def migrate_libvirt_vm_to_machine(vm: Dict[str, Any], networks: Dict[str, Any]) -> Dict[str, Any]:
    """Convert old libvirt VM format to new machine format."""
    machine = {
        'name': vm['name'],
        'type': 'libvirt',
        'openstack': {},
        'pm': {},
        'libvirt': {}
    }

    # OpenStack role mapping (profile -> role)
    profile_to_role = {
        'undercloud': 'undercloud',
        'controller': 'controller',
        'compute': 'compute',
        'cephstorage': 'CephStorage',
        'computehci': 'ComputeHCI',
        'computeovsdpdk': 'ComputeOvsDpdk',
        'computeovsdpdksriov': 'ComputeOvsDpdkSriov',
        'computesriov': 'ComputeSriov',
        'computeovshwoffload': 'ComputeOvsHwOffload',
    }

    if vm['profile'] != 'undercloud':
        machine['openstack']['role'] = profile_to_role.get(vm['profile'], vm['profile'])
        machine['openstack']['leaf'] = 'overcloud'

    # Power management (for overcloud VMs only)
    if 'bmcport' in vm:
        machine['pm'] = {
            'type': 'ipmi',
            'user': 'admin',
            'password': 'admin',
            'address': 'localhost',
            'port': vm['bmcport'],
            'mode': 'uefi' if vm.get('uefi', False) else 'bios'
        }

    # LibVirt-specific config
    # Convert memory from KiB to Gi (old format stores in KiB)
    memory_kib = vm.get('memory', 0)
    memory_gi = memory_kib / (1024 ** 2) if memory_kib > 0 else 8

    machine['libvirt'] = {
        'title': vm.get('title', ''),
        'hypervisor': vm.get('hypervisor', 'localhost'),
        'cpus': vm.get('vcpus', 2),
        'memory': f'{int(memory_gi)}Gi',
        'disks': [],
        'network': {
            'interfaces': []
        }
    }

    # Add root disk (old format stores in bytes)
    if vm.get('disk_size'):
        disk_bytes = vm['disk_size']
        disk_gi = disk_bytes / (1024 ** 3)
        machine['libvirt']['disks'].append({
            'root': True,
            'size': f'{int(disk_gi)}Gi'
        })

    # Add network interfaces
    if 'nics' in vm:
        for net_name, ip_or_empty in vm['nics'].items():
            # Map old network names to bridge names
            bridge_map = {
                'RHOSPVirtLab_ctlplane': 'br-ctlplane',
                'RHOSPVirtLab_management': 'br-management',
                'RHOSPVirtLab_external': 'br-external',
                'RHOSPVirtLab_tenant': 'br-tenant',
                'RHOSPVirtLab_storage': 'br-storage',
                'RHOSPVirtLab_storagemgmt': 'br-storagemgmt',
                'RHOSPVirtLab_internalapi': 'br-internalapi',
            }
            bridge = bridge_map.get(net_name, net_name)

            # Generate MAC address from VM mac + NIC index
            base_mac = vm.get('mac', '0c:1f:0d:00:00:00')
            # Ensure MAC has 6 octets (old format only had 5)
            mac_parts = base_mac.split(':')
            if len(mac_parts) == 5:
                mac_parts.append('00')  # Pad with :00

            # Modify last octet with NIC index to ensure uniqueness
            nic_index = len(machine['libvirt']['network']['interfaces'])
            mac_parts[-1] = f'{nic_index:02x}'
            mac = ':'.join(mac_parts)

            interface = {
                'name': f'nic{nic_index + 1}',
                'mac': mac,
                'bridge': bridge
            }
            machine['libvirt']['network']['interfaces'].append(interface)

    return machine


def migrate_physical_node_to_machine(node: Dict[str, Any]) -> Dict[str, Any]:
    """Convert old physical node format to new machine format."""
    machine = {
        'name': node['name'],
        'type': 'physical',
        'openstack': {
            'role': node.get('profile', 'compute'),
            'leaf': node.get('leaf', 'overcloud')
        },
        'pm': {
            'type': node.get('pm_type', 'ipmi'),
            'user': node.get('pm_user', 'admin'),
            'password': node.get('pm_password', 'admin'),
            'address': node.get('pm_addr', ''),
            'port': node.get('pm_port', '623'),
        },
        'physical': {
            'title': node.get('title', ''),
            'macs': []
        }
    }

    # Add MAC addresses
    if 'mac' in node:
        machine['physical']['macs'].append(node['mac'])

    # Add additional NICs if specified
    if 'nics' in node:
        for nic_name in node['nics'].values():
            # Note: this is a simplified mapping; actual NICs would need more info
            pass

    return machine


def migrate_networks_to_leafs(networks_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert old networks format to new leafs configuration."""
    # Create a default leaf from network definitions
    leaf = {
        'name': 'overcloud',
        'hypervisor': 'localhost',
        'ctlplane_bridge': {
            'name': 'br-ctlplane',
            'interface': None
        },
        'ctlplane_subnet': {
            'name': 'ctlplane-subnet',
            'cidr': '192.168.24.0/24',
            'gateway': '192.168.24.254',
            'vip': '192.168.24.253',
            'masquerade': False
        },
        'additional_bridges': [],
        'networks': []
    }

    # Map old network names to new network configurations
    network_map = {
        'RHOSPVirtLab_external': {
            'name': 'External',
            'bridge': 'br-external',
            'vip': True,
            'subnet': {
                'ip_subnet': '10.0.0.0/24',
                'gateway': '10.0.0.254',
                'vip': '10.0.0.253',
            }
        },
        'RHOSPVirtLab_tenant': {
            'name': 'Tenant',
            'bridge': 'br-ctlplane',
            'vip': False,
            'subnet': {
                'ip_subnet': '172.16.0.0/24',
                'vlan': 10
            }
        },
        'RHOSPVirtLab_storage': {
            'name': 'Storage',
            'bridge': 'br-ctlplane',
            'vip': True,
            'subnet': {
                'ip_subnet': '172.16.1.0/24',
                'vlan': 11,
                'vip': '172.16.1.253'
            }
        },
        'RHOSPVirtLab_storagemgmt': {
            'name': 'StorageMgmt',
            'bridge': 'br-ctlplane',
            'vip': True,
            'subnet': {
                'ip_subnet': '172.16.3.0/24',
                'vlan': 13,
                'vip': '172.16.3.253'
            }
        },
        'RHOSPVirtLab_internalapi': {
            'name': 'InternalApi',
            'bridge': 'br-ctlplane',
            'vip': True,
            'subnet': {
                'ip_subnet': '172.16.2.0/24',
                'vlan': 12,
                'vip': '172.16.2.253'
            }
        }
    }

    # Process networks from old format
    for net in networks_list:
        if net['name'] == 'RHOSPVirtLab_ctlplane':
            # Update ctlplane_subnet with actual values if different
            if 'ipv4' in net:
                ipv4 = net['ipv4']
                if 'address' in ipv4:
                    gateway = ipv4['address']
                    netmask = ipv4.get('netmask', '255.255.255.0')
                    # Convert netmask to CIDR
                    leaf['ctlplane_subnet']['gateway'] = gateway

        elif net['name'] == 'RHOSPVirtLab_management':
            # Add to additional_bridges
            if 'ipv4' in net:
                ipv4 = net['ipv4']
                bridge_config = {
                    'name': 'br-management',
                    'interface': net.get('interface'),
                    'ipv4': {
                        'address': ipv4.get('address', '192.168.250.1')
                    }
                }
                leaf['additional_bridges'].append(bridge_config)

        elif net['name'] in network_map:
            net_config = network_map[net['name']].copy()
            # Update with any VLAN info from old format
            if 'vlan' in net:
                if 'subnet' not in net_config:
                    net_config['subnet'] = {}
                net_config['subnet']['vlan'] = net['vlan']
            leaf['networks'].append(net_config)

    return leaf


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    old_vars_dir = sys.argv[1]
    new_vars_dir = sys.argv[2]

    # Create output directory if it doesn't exist
    Path(new_vars_dir).mkdir(parents=True, exist_ok=True)

    # Load old configuration files
    print(f"Loading old configuration from {old_vars_dir}...")
    vms_data = load_yaml(os.path.join(old_vars_dir, 'vms.yml'))
    physical_data = load_yaml(os.path.join(old_vars_dir, 'physical.yml'))
    networks_data = load_yaml(os.path.join(old_vars_dir, 'networks.yml'))
    options_data = load_yaml(os.path.join(old_vars_dir, 'options.yml'))

    # Migrate configuration
    new_config = {'undercloud': {}, 'machines': []}

    # Migrate VMs
    vms_list = vms_data.get('vms', [])
    networks_list = networks_data.get('networks', [])

    for vm in vms_list:
        machine = migrate_libvirt_vm_to_machine(vm, networks_list)
        if vm['profile'] == 'undercloud':
            new_config['undercloud'] = machine
        else:
            new_config['machines'].append(machine)

    # Migrate physical nodes
    physical_list = physical_data.get('physical', [])
    for node in physical_list:
        machine = migrate_physical_node_to_machine(node)
        new_config['machines'].append(machine)

    # Write machines.yml
    machines_output = os.path.join(new_vars_dir, 'machines.yml')
    print(f"Writing migrated machines to {machines_output}...")
    with open(machines_output, 'w') as f:
        f.write("---\n")
        f.write("# Migrated from old vms.yml and physical.yml format\n")
        f.write("# Review and adjust as needed\n\n")
        yaml.dump(new_config, f, default_flow_style=False)

    # Migrate leafs from networks
    leafs = [migrate_networks_to_leafs(networks_list)]

    # Handle options.yml migration
    custom_options = {}
    deprecated_options = {}

    # Extract custom options that might differ from defaults
    # Skip empty strings and None values
    for key in ['RHOSP_version', 'RHOSP_release', 'external_if', 'dns_servers', 'ntp_servers',
                'vncproxy', 'BmcUsername', 'BmcPassword', 'OvercloudAdminPassword',
                'DeployOctavia', 'DeployDesignate', 'DeployFrr', 'RegisterNodes',
                'LowMemUsage', 'ControllersFencing', 'NeutronDriver', 'UndercloudFullUpdate',
                'DisableTelemetry', 'CustomRhelImage', 'CustomCirrOSImage', 'CustomOcClientUrl']:
        if key in options_data and options_data[key] not in ('', None):
            custom_options[key] = options_data[key]

    # Track deprecated options that are no longer used
    if 'overcloud_ip' in options_data:
        deprecated_options['overcloud_ip'] = options_data['overcloud_ip']
    if 'forwarded_ports' in options_data:
        deprecated_options['forwarded_ports'] = options_data['forwarded_ports']

    # Merge options into vars/options.yml while preserving structure
    options_file = os.path.join(new_vars_dir, 'options.yml')
    if os.path.exists(options_file):
        update_options_file(options_file, custom_options, leafs if networks_list else None)
        print(f"\nMigration complete!")
        print(f"✓ {machines_output}")
        print(f"✓ {options_file} (merged custom options)")
    else:
        print(f"\nMigration complete!")
        print(f"✓ {machines_output}")
        print(f"\n⚠ {options_file} not found. Output migrated options:")
        if custom_options:
            print(f"\n# Custom options:")
            for key, value in custom_options.items():
                yaml.dump({key: value}, sys.stdout, default_flow_style=False)
        if networks_list:
            print(f"\n# Leafs configuration:")
            yaml.dump({'leafs': leafs}, sys.stdout, default_flow_style=False)

    if deprecated_options:
        print(f"\nNote: The following old options are no longer used in the new format:")
        print(f"  - overcloud_ip: now computed from leaf's External network VIP")
        print(f"  - forwarded_ports: now hardcoded in role vars/main.yml")
        print(f"Old values (for reference):")
        for key, value in deprecated_options.items():
            print(f"  {key}: {value}")

    print(f"\nNext steps:")
    print(f"1. Review {machines_output} for accuracy")
    print(f"2. Review vars/options.yml for any additional customizations")
    print(f"3. Test the configuration with a dry-run")
    print(f"\nNote: This script provides a best-effort migration. Some fields may need manual adjustment:")
    print(f"  - SSH key configurations (id_rsa.pub location)")
    print(f"  - DHCP ranges for networks")
    print(f"  - Allocation pools for subnets")
    print(f"  - Any custom network configurations")
    print(f"  - Profile-to-role mappings for custom profiles")


if __name__ == '__main__':
    main()
