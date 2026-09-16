#!/usr/bin/env python3
"""
Migrate old var format (vms.yml, physical.yml, networks.yml) to new format (machines.yml).

Usage:
    python3 migrate-vars-to-new-format.py <path_to_old_vars_dir> <path_to_new_vars_dir>

This script reads the old configuration and updates the new skeleton files with values
from the old configuration, preserving the new file structure and comments.
"""

import sys
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any


def load_yaml(filepath: str) -> Dict[str, Any]:
    """Load YAML file safely."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}


def migrate_vms(vms_list: List[Dict[str, Any]]) -> tuple:
    """Convert old VMs to new format, returning undercloud dict and machines list."""
    undercloud = {}
    machines = []

    profile_to_role = {
        'undercloud': 'undercloud',
        'controller': 'controller',
        'compute': 'compute',
        'cephstorage': 'CephStorage',
        'computehci': 'ComputeHCI',
    }

    for vm in vms_list:
        machine = {
            'name': vm['name'],
            'type': 'libvirt',
            'openstack': {},
            'pm': {},
            'libvirt': {
                'title': vm.get('title', ''),
                'hypervisor': vm.get('hypervisor', 'localhost'),
                'cpus': vm.get('vcpus', 2),
                'memory': f"{int(vm.get('memory', 0) / (1024 ** 2))}Gi",
                'disks': [],
                'network': {'interfaces': []}
            }
        }

        # Add root disk
        if vm.get('disk_size'):
            disk_gi = int(vm['disk_size'] / (1024 ** 3))
            machine['libvirt']['disks'].append({'root': True, 'size': f'{disk_gi}Gi'})

        # Add NICs
        if 'nics' in vm:
            base_mac = vm.get('mac', '0c:1f:0d:00:00:00')
            mac_parts = base_mac.split(':')
            if len(mac_parts) == 5:
                mac_parts.append('00')

            bridge_map = {
                'RHOSPVirtLab_ctlplane': 'br-ctlplane',
                'RHOSPVirtLab_management': 'br-management',
                'RHOSPVirtLab_external': 'br-external',
            }

            for net_name in vm['nics'].keys():
                bridge = bridge_map.get(net_name, net_name)
                nic_index = len(machine['libvirt']['network']['interfaces'])
                mac_parts[-1] = f'{nic_index:02x}'
                mac = ':'.join(mac_parts)

                machine['libvirt']['network']['interfaces'].append({
                    'name': f'nic{nic_index + 1}',
                    'mac': mac,
                    'bridge': bridge
                })

        if vm['profile'] == 'undercloud':
            # Remove management interface from undercloud (it's implicit)
            machine['libvirt']['network']['interfaces'] = [
                iface for iface in machine['libvirt']['network']['interfaces']
                if iface['bridge'] != 'br-management'
            ]
            undercloud = machine
        else:
            machine['openstack'] = {
                'role': profile_to_role.get(vm['profile'], vm['profile']),
                'leaf': 'overcloud'
            }
            machine['pm'] = {
                'type': 'ipmi',
                'user': 'admin',
                'password': 'admin',
                'address': 'localhost',
                'port': vm.get('bmcport', 6230),
                'mode': 'uefi' if vm.get('uefi') else 'bios'
            }
            machines.append(machine)

    return undercloud, machines


def transform_old_leaf_to_new_format(old_leaf: Dict[str, Any]) -> Dict[str, Any]:
    """Transform old DefaultLeaf0 format to new leafs format."""
    new_leaf = {
        'name': old_leaf.get('name', 'overcloud'),
        'hypervisor': old_leaf.get('hypervisor', 'localhost'),
        'ctlplane_bridge': {
            'name': 'br-ctlplane',
            'interface': None
        },
        'ctlplane_subnet': {
            'name': old_leaf.get('subnet', {}).get('name', 'ctlplane-subnet'),
            'cidr': old_leaf.get('subnet', {}).get('cidr', '192.168.24.0/24'),
            'gateway': old_leaf.get('subnet', {}).get('gateway', '192.168.24.254'),
            'vip': old_leaf.get('subnet', {}).get('vip', '192.168.24.253'),
            'masquerade': old_leaf.get('subnet', {}).get('masquerade', False),
            'dhcp_start': old_leaf.get('subnet', {}).get('dhcp_start'),
            'dhcp_end': old_leaf.get('subnet', {}).get('dhcp_end'),
            'inspection_iprange': old_leaf.get('subnet', {}).get('inspection_iprange'),
        },
        'additional_bridges': [],
        'networks': []
    }

    # Map old network names to new network names
    name_map = {
        'External': 'External',
        'Tenant': 'Tenant',
        'Storage': 'Storage',
        'StorageMgmt': 'StorageMgmt',
        'InternalApi': 'InternalApi',
        'Management': 'Management',
    }

    # Process old networks format
    old_networks = old_leaf.get('networks', {})
    for old_name, old_net_data in old_networks.items():
        new_name = name_map.get(old_name, old_name)

        # Extract prefix and build CIDR
        prefix = old_net_data.get('prefix', '')
        vlan = old_net_data.get('vlan')

        # Map network name to bridge (VLANs go on br-ctlplane, External on br-external)
        if old_name == 'External':
            bridge = 'br-external'
        else:
            bridge = 'br-ctlplane'

        network = {
            'name': new_name,
            'bridge': bridge,
            'vip': True,
            'mtu': 1500,
            'subnet': {}
        }

        if prefix:
            # Infer /24 CIDR from prefix
            network['subnet']['ip_subnet'] = f'{prefix}.0/24'
            if vlan:
                network['subnet']['vlan'] = vlan
                network['subnet']['gateway'] = f'{prefix}.254'
                network['subnet']['vip'] = f'{prefix}.253'
            else:
                # No VLAN means it's on native VLAN
                network['subnet']['gateway'] = f'{prefix}.254'
                network['subnet']['vip'] = f'{prefix}.253'

        new_leaf['networks'].append(network)

    return new_leaf


def format_machine(machine: Dict[str, Any], is_undercloud: bool = False) -> str:
    """Format a machine dict as YAML with proper indentation."""
    if is_undercloud:
        return yaml.dump({'undercloud': machine}, default_flow_style=False)
    else:
        return yaml.dump({'machines': [machine]}, default_flow_style=False)[10:]  # Skip "machines:\n"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    old_vars_dir = sys.argv[1]
    new_vars_dir = sys.argv[2]

    Path(new_vars_dir).mkdir(parents=True, exist_ok=True)

    print(f"Loading old configuration from {old_vars_dir}...")
    vms_data = load_yaml(os.path.join(old_vars_dir, 'vms.yml'))
    networks_data = load_yaml(os.path.join(old_vars_dir, 'networks.yml'))
    options_data = load_yaml(os.path.join(old_vars_dir, 'options.yml'))

    # Migrate machines
    vms_list = vms_data.get('vms', [])
    undercloud, machines = migrate_vms(vms_list)

    # Extract DefaultLeaf0 from options.yml if present
    default_leaf_from_options = options_data.get('DefaultLeaf0', {})

    # Generate machines.yml from template
    machines_template = os.path.join(new_vars_dir, 'machines.yml')

    if not os.path.exists(machines_template):
        print(f"Error: Template {machines_template} not found")
        sys.exit(1)

    with open(machines_template, 'r') as f:
        template_content = f.read()

    # Find where to insert undercloud (after the first comment block)
    lines = template_content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('undercloud:'):
            # Replace the undercloud section
            end_idx = i + 1
            while end_idx < len(lines) and (lines[end_idx].startswith('  ') or lines[end_idx].strip() == ''):
                end_idx += 1
            undercloud_yaml = yaml.dump(undercloud, default_flow_style=False)
            # Indent all lines of the undercloud YAML by 2 spaces
            indented_lines = ['undercloud:']
            for yaml_line in undercloud_yaml.rstrip('\n').split('\n'):
                indented_lines.append('  ' + yaml_line)
            lines[i:end_idx] = indented_lines
            break

    # Find and replace machines section
    for i, line in enumerate(lines):
        if line.startswith('machines:'):
            end_idx = i + 1
            while end_idx < len(lines) and (lines[end_idx].startswith('- ') or lines[end_idx].startswith('  ')):
                end_idx += 1

            # Generate new machines
            new_machines_lines = ['machines:']
            for machine in machines:
                machine_yaml = yaml.dump(machine, default_flow_style=False)
                # Indent machine lines (add "- " to first line and "  " to others)
                machine_lines = machine_yaml.rstrip('\n').split('\n')
                new_machines_lines.append('- ' + machine_lines[0])
                for mline in machine_lines[1:]:
                    if mline.strip():  # Only add non-empty lines
                        new_machines_lines.append('  ' + mline)
                    else:
                        new_machines_lines.append(mline)

            lines[i:end_idx] = new_machines_lines
            break

    # Write updated machines.yml
    machines_output = os.path.join(new_vars_dir, 'machines.yml')
    with open(machines_output, 'w') as f:
        f.write('\n'.join(lines))

    print(f"✓ {machines_output}")

    # Update options.yml with values from old options.yml, preserving order and structure
    options_output = os.path.join(new_vars_dir, 'options.yml')
    if os.path.exists(options_output):
        with open(options_output, 'r') as f:
            options_lines = f.readlines()

        # Keys to look for and update
        update_keys = {
            'RHOSP_version', 'RHOSP_release', 'external_if', 'dns_servers', 'ntp_servers',
            'vncproxy', 'BmcUsername', 'BmcPassword', 'OvercloudAdminPassword',
            'DeployOctavia', 'DeployDesignate', 'DeployFrr', 'RegisterNodes',
            'LowMemUsage', 'ControllersFencing', 'NeutronDriver', 'UndercloudFullUpdate',
            'DisableTelemetry'
        }

        new_lines = []
        i = 0
        while i < len(options_lines):
            line = options_lines[i]
            matched = False

            # Check if this line starts a key we want to update
            for key in update_keys:
                if line.strip().startswith(f'{key}:'):
                    if key in options_data and options_data[key] not in ('', None):
                        value = options_data[key]
                        indent = len(line) - len(line.lstrip())

                        # Skip old value lines (everything indented under this key)
                        j = i + 1
                        while j < len(options_lines):
                            next_line = options_lines[j]
                            if next_line.strip() == '' or next_line.lstrip().startswith('#'):
                                j += 1
                                continue
                            next_indent = len(next_line) - len(next_line.lstrip())
                            if next_indent > indent:
                                j += 1
                            else:
                                break

                        # Write new value
                        if isinstance(value, list):
                            new_lines.append(f"{' ' * indent}{key}:\n")
                            for item in value:
                                new_lines.append(f"{' ' * (indent + 2)}- '{item}'\n")
                        else:
                            new_lines.append(f"{' ' * indent}{key}: {value}\n")

                        i = j
                        matched = True
                    break

            if not matched:
                new_lines.append(line)
                i += 1

        # Replace leafs with transformed DefaultLeaf0 if present
        if default_leaf_from_options:
            new_leaf = transform_old_leaf_to_new_format(default_leaf_from_options)
            print(f"Transformed leaf networks:")
            for net in new_leaf.get('networks', []):
                print(f"  {net['name']}: vlan={net.get('subnet', {}).get('vlan', 'none')}")

            new_lines_with_leafs = []
            i = 0
            while i < len(new_lines):
                line = new_lines[i]
                if line.strip().startswith('leafs:'):
                    # Skip old leafs block
                    j = i + 1
                    while j < len(new_lines):
                        next_line = new_lines[j]
                        if next_line.strip() == '' or next_line.lstrip().startswith('#'):
                            j += 1
                            continue
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent > 0:
                            j += 1
                        else:
                            break
                    # Write new leafs from transformed DefaultLeaf0
                    leafs_yaml = yaml.dump({'leafs': [new_leaf]}, default_flow_style=False)
                    formatted_lines = leafs_yaml.rstrip('\n').split('\n')
                    new_lines_with_leafs.extend([line + '\n' for line in formatted_lines])
                    i = j
                else:
                    new_lines_with_leafs.append(line)
                    i += 1
            new_lines = new_lines_with_leafs

        with open(options_output, 'w') as f:
            f.writelines(new_lines)

        print(f"✓ {options_output}")

    if 'overcloud_ip' in options_data or 'forwarded_ports' in options_data:
        print(f"\nNote: Deprecated options not migrated:")
        print(f"  - overcloud_ip: now computed from leaf's External network VIP")
        print(f"  - forwarded_ports: now hardcoded in role vars/main.yml")

    print(f"\nMigration complete!")
    print(f"Next steps:")
    print(f"1. Review {machines_output} for accuracy")
    print(f"2. Review {options_output} for any customizations")
    print(f"3. Test the configuration with a dry-run")


if __name__ == '__main__':
    main()
