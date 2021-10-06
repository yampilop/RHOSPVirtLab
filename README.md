# RHOSP 16.1 Virtual Lab

Virtual lab to setup a Red Hat OpenStack Platform test installation in your personal computer

![Overview](/images/overview.png)

## Assumptions

This document assumes that you run a **Fedora 34** installation in your personal computer. The steps for other versions of Fedora and other Linux-based OS may differ from the exposed here.

## Installation

### Install libvirt and virt-manager

```
sudo yum install virt-manager libvirt
```

### Import XML files

You need to import networks matching the following XML files:

- libvirt-xmls
  - [default.xml](libvirt-xmls/default.xml)
  - [provisioning.xml](libvirt-xmls/provisioning.xml)

To do that, just run:

```
sudo virsh net-define <XML_FILE>
```

List the networks to verify they were created:

```
$ sudo virsh net-list 
 Name           State    Autostart   Persistent
-------------------------------------------------
 default        active   yes         yes
 provisioning   active   yes         yes
```

You also need to import the virtual machines (domains) matching the following XML files:

- libvirt-xmls
  - [undercloud.xml](libvirt-xmls/undercloud.xml)
  - [controller0.xml](libvirt-xmls/controller0.xml)
  - [compute0.xml](libvirt-xmls/compute0.xml)
  - [compute1.xml](libvirt-xmls/compute1.xml)

To do that, just run:
```
sudo virsh define <XML_FILE>
```

List the domains to verify they were created:

```
$ sudo virsh list --all
 Id   Name          State
------------------------------
 -    compute0      shut off
 -    compute1      shut off
 -    controller0   shut off
 -    director      shut off
```

The resulting Virtual Machine Manager screen should look like the following picture:

![Virtual Machine Manager](/images/VMM.png)

The size of the disk images should be as the following image:

![Storage sizes](/images/storage.png)

The storage from undercloud node should be created based on the **Red Hat Enterprise Linux 8.2 Update KVM Guest Image** ([rhel-8.2-update-2-x86_64-kvm.qcow2](https://access.redhat.com/downloads/content/479/ver=/rhel---8/8.2/x86_64/product-software)):

![Storage sizes](/images/undercloud_img.png)

To customize ***cloud-user*** password, add a CDROM device with the cloud-init configuration iso file found [here](https://gitlab.com/neyder/rhel-cloud-init/-/raw/master/rhel-cloud-init.iso).

![Storage sizes](/images/undercloud_cdrom.png)

### Install and configure virtualbmc

Install the packages:

```
sudo yum install python3-virtualbmc ipmitool
```

Enable and start the vbmcd service:

```
sudo systemctl enable --now vbmcd
```

Create the binding ports for the IPMI controller machines:

```
vbmc add --username admin --password admin --address 192.168.122.1 --port 6230 controller0
vbmc add --username admin --password admin --address 192.168.122.1 --port 6231 compute0
vbmc add --username admin --password admin --address 192.168.122.1 --port 6232 compute1
```

List the ports:

```
$ vbmc list
+-------------+---------+---------------+------+
| Domain name | Status  | Address       | Port |
+-------------+---------+---------------+------+
| compute0    | down    | 192.168.122.1 | 6231 |
| compute1    | down    | 192.168.122.1 | 6232 |
| controller0 | down    | 192.168.122.1 | 6230 |
+-------------+---------+---------------+------+
```

Start the vbmc listening ports:

```
vbmc start controller0
vbmc start compute0
vbmc start compute1
```

List the ports again:

```
$ vbmc list
+-------------+---------+---------------+------+
| Domain name | Status  | Address       | Port |
+-------------+---------+---------------+------+
| compute0    | running | 192.168.122.1 | 6231 |
| compute1    | running | 192.168.122.1 | 6232 |
| controller0 | running | 192.168.122.1 | 6230 |
+-------------+---------+---------------+------+
```

Test the status of controller0 as an example:

```
$ ipmitool -I lanplus -U admin -P admin -H 192.168.122.1 -p 6230 power status
Chassis Power is off
```

If you are using firewalld, you should open the ports in the libvirtd zone:

```
firewall-cmd --zone=libvirt --add-port=6230-6232/udp --permanent 
firewall-cmd --zone=libvirt --add-port=6230-6232/udp
```

## RHOSP 16.1 installation

### First login

Start undercloud virtual machine. Once it has booted, login as ***cloud-user*** using the password ***redhat***.

Change to the root user:

```
sudo -i
```

### Initial steps

Create the stack user, set a password and configure sudo permissions:

```
useradd stack
passwd stack
echo "stack ALL=(root) NOPASSWD:ALL" | tee -a /etc/sudoers.d/stack
chmod 0440 /etc/sudoers.d/stack
```

Change to stack user and 

```
su - stack
```

Create the first directories:

```
mkdir /home/stack/images
mkdir /home/stack/templates
```

Change the hostname:

```
sudo hostnamectl set-hostname undercloud.localdomain
sudo hostnamectl set-hostname --transient undercloud.localdomain
```

### Red Hat subscription registration

Register your system using your Red Hat valid credentials:
```
sudo subscription-manager register
```

Attach the subscription to a valid Openstack pool and set the release to the 8.2 version:

```
sudo subscription-manager list --available --all --matches="Red Hat OpenStack"
sudo subscription-manager attach --pool=XXXXXXXXXXX
sudo subscription-manager release --set=8.2
```

Disable all the repos and enable only the needed:

```
sudo subscription-manager repos --disable=*

sudo subscription-manager repos \
--enable=rhel-8-for-x86_64-baseos-eus-rpms \
--enable=rhel-8-for-x86_64-appstream-eus-rpms \
--enable=rhel-8-for-x86_64-highavailability-eus-rpms \
--enable=ansible-2.9-for-rhel-8-x86_64-rpms \
--enable=openstack-16.1-for-rhel-8-x86_64-rpms \
--enable=fast-datapath-for-rhel-8-x86_64-rpms \
--enable=advanced-virt-for-rhel-8-x86_64-rpms \
--enable=rhceph-4-tools-for-rhel-8-x86_64-rpms
```

Set the right module streams:

```
sudo dnf module disable -y container-tools:rhel8
sudo dnf module enable -y container-tools:2.0

sudo dnf module disable -y virt:rhel
sudo dnf module enable -y virt:8.2
```

Disable cloud-init:

```
sudo systemctl disable --now cloud-init
```

Install some useful tools:

```
sudo yum install -y vim wget bash-completion python3-argcomplete
```

Update the system:

```
sudo dnf update -y
```

Reboot the machine:

```
sudo reboot
```

### Install the needed packages

```
sudo dnf install -y python3-tripleoclient ceph-ansible rhosp-director-images rhosp-director-images-ipa
```

### Prepare the files for undercloud installation

```
openstack tripleo container image prepare default \
--local-push-destination \
--output-env-file containers-prepare-parameter.yaml

cp /usr/share/python-tripleoclient/undercloud.conf.sample /home/stack/undercloud.conf
```

Edit the undercloud.conf file to match the following parameters:

```
[DEFAULT]
container_images_file = /home/stack/containers-prepare-parameter.yaml
custom_env_files = /home/stack/templates/custom-undercloud-params.yaml
enable_node_discovery = true
local_interface = eth0
local_ip = 192.168.24.1/24
local_subnet = ctlplane-subnet
overcloud_domain_name = localdomain
undercloud_admin_host = 192.168.24.3
undercloud_nameservers = 8.8.8.8,8.8.4.4
undercloud_ntp_servers = 0.pool.ntp.org,1.pool.ntp.org,2.pool.ntp.org,3.pool.ntp.org
undercloud_public_host = 192.168.24.2
[ctlplane-subnet]
cidr = 192.168.24.0/24
dhcp_end = 192.168.24.55
dhcp_start = 192.168.24.5
gateway = 192.168.24.1
inspection_iprange = 192.168.24.100,192.168.24.120
masquerade = true
```

Edit /etc/hosts and ensure there are no undercloud names in the lines starting with 127.0.0.1 and ::1. There should be just localhost names there.

Create a /home/stack/templates/custom-undercloud-params.yaml file with the following content:

```
  parameter_defaults:
    AdminPassword: "redhat"
    AdminEmail: "admin@example.com"
```

Edit the containers-prepare-parameter.yaml file adding this to the end (ensure to put your credentials):

```
  ContainerImageRegistryLogin: true
  ContainerImageRegistryCredentials:
    registry.redhat.io:
      <username>: '<password>'
```

### Disable NetworkManager and enable network.service

```
sudo systemctl stop NetworkManager
sudo systemctl disable NetworkManager
```

Delete other interfaces ifcfg files from /etc/sysconfig/network-scripts, except the **ifcfg-eth1**.

Enable and start network.service.

```
sudo systemctl enable --now network.service
```

This service should start with no error. Otherwise you should review the network-scripts files looking for misconfigurations.

### Undercloud installation

```
openstack undercloud install
```

This command should finish with no error.

### Configure the external gateway inside the undercloud

Add a /etc/sysconfig/network-scripts/ifcfg-vlan10 file with the following content:

```
BOOTPROTO=none
IPADDR=10.0.0.1
PREFIX=24
DEFROUTE=no
IPV4_FAILURE_FATAL=no
IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=2001:db8:fd00:1000::/64
IPV6_DEFROUTE=no
IPV6_FAILURE_FATAL=no
IPV6_ADDR_GEN_MODE=stable-privacy
NAME=vlan10
DEVICE=vlan10
ONBOOT=yes
NM_CONTROLLED=no
```

Edit the /etc/sysconfig/network-scripts/ifcfg-br-ctlplane file and add the following to OVS_EXTRA parameter at the end:

```
 -- add-port br-ctlplane vlan10 tag=10 -- set interface vlan10 type=internal
```

Restart network.service ensuring there is no error:

```
sudo systemctl restart network
```

### Preparing overcloud images

Prepare the overcloud images and load them to openstack:

```
cd /home/stack/images
for i in /usr/share/rhosp-director-images/overcloud-full-latest-16.1.tar /usr/share/rhosp-director-images/ironic-python-agent-latest-16.1.tar; do tar -xvf $i; done
source stackrc
openstack overcloud image upload --image-path /home/stack/images/
```

List images:

```
openstack image list --fit-width
```
  
### Prepare the overcloud template files

Create a /home/stack/instackenv.yaml file with the following content:
```
nodes:
  - ports:
      - address: 0c:1f:0d:6f:06:00
        physical_network: ctlplane
    name: "controller0"
    capabilities: "profile:control,boot_option:local"
    cpu: 6
    memory: 8192
    disk: 50
    arch: "x86_64"
    pm_type: "ipmi"
    pm_user: "admin"
    pm_password: "admin"
    pm_addr: "192.168.122.1"
    pm_port: "6230"
  - ports:
      - address: 0c:1f:0d:2f:e1:00
        physical_network: ctlplane
    name: "compute0"
    capabilities: "profile:compute,boot_option:local"
    cpu: 4
    memory: 8192
    disk: 50
    arch: "x86_64"
    pm_type: "ipmi"
    pm_user: "admin"
    pm_password: "admin"
    pm_addr: "192.168.122.1"
    pm_port: "6231"
  - ports:
      - address: 0c:1f:0d:2f:e2:00
        physical_network: ctlplane
    name: "compute1"
    capabilities: "profile:compute,boot_option:local"
    cpu: 4
    memory: 8192
    disk: 50
    arch: "x86_64"
    pm_type: "ipmi"
    pm_user: "admin"
    pm_password: "admin"
    pm_addr: "192.168.122.1"
    pm_port: "6232"
```

Import the bremetal nodes:

```
source /home/stack/stackrc
openstack overcloud node import --validate-only /home/stack/instackenv.yaml
openstack overcloud node import /home/stack/instackenv.yaml
openstack baremetal node list
```

Run validations (you can ignore the undercloud-neutron-sanity-check FAILED):

```
openstack tripleo validator run --group pre-introspection
```

Introspect the nodes:

```
openstack overcloud node introspect --all-manageable --provide
```

After the process finishes, the nodes must be in available state:

```
openstack baremetal node list
```

List the profiles to check if they match the configuration:

```
openstack overcloud profiles list
```

Generate the roles file:

```
source stackrc
openstack overcloud roles generate \
--roles-path /usr/share/openstack-tripleo-heat-templates/roles \
-o /home/stack/templates/roles_data.yaml \
Controller Compute
```

Create a /home/stack/templates/node-info.yaml file with the following content:

```
parameter_defaults:
  OvercloudControllerFlavor: control
  OvercloudComputeFlavor: compute
  ControllerCount: 1
  ComputeCount: 2
```

Prepare the images for containers:

```
sudo openstack tripleo container image prepare -e /home/stack/templates/containers-prepare-parameter.yaml --output-env-file overcloud-images.yaml
```

Configure the physical networks for later provider network configurations. To do that, create a /home/stack/templates/physical_networks.yaml file with the following contents:

```
parameter_defaults:
  NeutronBridgeMappings: "datacentre:br-ctlplane"
  NeutronPhysicalBridge: "br-ctlplane"
```

Create a /home/stack/templates/nova-custom-config.yaml file with the following content to customize nova filter:
```
parameter_defaults:
  ControllerExtraConfig:
    nova::scheduler::filter::scheduler_host_subset_size: '999'
```

### Deploy the overcloud

Execute the deploy command with all the templates and environment files:

```
openstack overcloud deploy \
--log-file overcloud_deployment.log \
--timeout 120 \
--templates /usr/share/openstack-tripleo-heat-templates/ \
--stack overcloud \
--ntp-server rhel.pool.ntp.org \
-r /home/stack/templates/roles_data.yaml \
-e /home/stack/templates/node-info.yaml \
-e /home/stack/templates/nova-custom-config.yaml \
-e /home/stack/containers-prepare-parameter.yaml \
-e /home/stack/overcloud-images.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/network-isolation.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/network-environment.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/net-single-nic-with-vlans.yaml \
-e /home/stack/templates/physical_networks.yaml
```

The output should end with the following:

```
Ansible passed.
Overcloud configuration completed.
Overcloud Endpoint: http://10.0.0.X:5000
Overcloud Horizon Dashboard URL: http://10.0.0.X:80/dashboard
Overcloud rc file: /home/stack/overcloudrc
Overcloud Deployed without error
```

***Take note of the Overcloud Horizon Dashboard URL***

### After deploy tasks

Masquerade external network traffic to allow dashboard navigation:

```
sudo iptables -t nat -A POSTROUTING -j MASQUERADE -s 10.0.0.0/24 -m state --state NEW,RELATED,ESTABLISHED -m comment --comment "CUSTOM masquerade external network traffic"
sudo service iptables save
```

### Open dashboard

From a web browser, open the Overcloud Horizon Dashboard URL and login as **admin** using the password inside the /home/stack/overcloudrc file.
