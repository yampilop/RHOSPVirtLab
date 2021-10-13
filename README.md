# RHOSP 16.1 Virtual Lab

Virtual lab to setup a Red Hat OpenStack Platform test installation in your personal computer

![Overview](/images/overview.png)

![Network diagram](/images/network_diagram.svg)

## Assumptions

This document assumes that you run a **Fedora 34** installation in your personal computer. The steps for other versions of Fedora and other Linux-based OS may differ from the exposed here.

## Local user configuration

The user from which you will execute the lab needs to have sudo permissions enabled. Also needs to be part of the libvirt and the kvm groups. To add it to those groups execute:

```
sudo usermod -aG libvirt $USERNAME
sudo usermod -aG kvm $USERNAME
```

After that you need to logout and login again for the changes to take effect.

## Pull the repo

Move to a directory where you want to work, for example the home directory:

```
cd ~
```

Clone the repository and enter the directory.

```
git clone https://github.com/yampilop/RHOSPVirtLab.git
cd RHOSPVirtLab
```

## Clean the installation

To start/restart the installation from scratch, a playbook is provided to clean everything in the local machine. Every progress in the lab will be erased. Please **be careful** with this command:

```
ansible-playbook clean.yml
```

## Initial configurations

### Download the RHEL8.2 QCOW2 image and custom ISO

The storage from undercloud node will be created based on the **Red Hat Enterprise Linux 8.2 Update KVM Guest Image** ([rhel-8.2-x86_64-kvm.qcow2](https://access.redhat.com/downloads/content/479/ver=/rhel---8/8.2/x86_64/product-software)).

To customize cloud-user password, you need the cloud-init configuration iso file [rhel-cloud-init.iso](https://gitlab.com/neyder/rhel-cloud-init/-/raw/master/rhel-cloud-init.iso).

**Download** those images and place them in the ***storage*** folder inside the working directory.

### Install ansible

```
sudo yum install ansible
```

### Test user and ansible installation

```
$ ansible local -m ping

workstation | SUCCESS => {

    ...

    "ping": "pong"
}

```

### Install requirements

```
ansible-galaxy collection install -r requirements.yml
```

## Create a vault for credentials

You need to create a vault file to store your Red Hat Subscription credentials. To do that, execute the following command:

```
ansible-vault create vault_credentials.yaml
```

You will write the credentials in the following format:

```
rh_username: '<USERNAME>'
rh_password: '<PASSWORD>'
```

## Execute the Ansible Playbook

Execute the playbook with the following command (you will be prompted for the user password and the vault password):

```
ansible-playbook --ask-vault-pass playbook.yml
```

## Last steps

As the undercloud installation and overcloud deploy are tasks that last longer and require attention due to possible failures, they need to be executed manually. To do that, login to the undercloud:

```
ssh stack@undercloud
```

### Install the undercloud

Execute the following command:

```
openstack undercloud install
```

Wait for the process to finish with the following output:

```
########################################################

Deployment successful!

########################################################

Writing the stack virtual update mark file /var/lib/tripleo-heat-installer/update_mark_undercloud

##########################################################

The Undercloud has been successfully installed.

Useful files:

Password file is at /home/stack/undercloud-passwords.conf
The stackrc file is at ~/stackrc

Use these files to interact with OpenStack services, and
ensure they are secured.

##########################################################
```

### Prepare the overcloud

Load the overcloud images to openstack:

```
source /home/stack/stackrc
openstack overcloud image upload --image-path /home/stack/images/
```

List images:

```
openstack image list --fit-width
```

Import the bremetal nodes:

```
source /home/stack/stackrc
openstack overcloud node import --validate-only /home/stack/templates/instackenv.yaml
openstack overcloud node import /home/stack/templates/instackenv.yaml
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
source /home/stack/stackrc
openstack overcloud roles generate \
--roles-path /usr/share/openstack-tripleo-heat-templates/roles \
-o /home/stack/templates/roles_data.yaml \
Controller Compute
```

Prepare the images for containers:

```
sudo openstack tripleo container image prepare -e /home/stack/templates/containers-prepare-parameter.yaml --output-env-file /home/stack/templates/overcloud-images.yaml
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
-e /home/stack/templates/containers-prepare-parameter.yaml \
-e /home/stack/templates/overcloud-images.yaml \
-e /home/stack/templates/custom-overcloud.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/network-isolation.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/network-environment.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/net-multiple-nics.yaml
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

### Open dashboard

From a web browser, open the Overcloud Horizon Dashboard URL and login as **admin** using the password inside the /home/stack/overcloudrc file.