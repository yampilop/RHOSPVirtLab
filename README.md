# RHOSP 16.2 Virtual Lab

Virtual lab to setup a Red Hat OpenStack Platform test installation in your personal computer.

## Assumptions

This document assumes that you run a **Fedora 34** installation in your personal computer. The steps for other versions of Fedora and other Linux-based OS may differ from the exposed here.

Your personal computer must fulfill the following **minimum requirements**:

  * CPU: 12 cores
  * RAM: 32GB
  * Disk: 250GB of free space

## Local user configuration

The user from which you will execute the lab needs to have `sudo` **permissions enabled**.

Also needs to be part of the `libvirt` and the `kvm` groups. To add it to those groups execute:

```bash
sudo usermod -aG libvirt $USERNAME
sudo usermod -aG kvm $USERNAME
```

After that you need to logout and login again for the changes to take effect.

## Pull the repo

Move to a directory where you want to work, for example the home directory:

```bash
cd ~
```

Clone the repository and enter the directory.

```bash
git clone https://github.com/yampilop/RHOSPVirtLab.git
cd RHOSPVirtLab
```

## Initial configurations

### Download the RHEL8.4 QCOW2 image and custom ISO

The storage from `undercloud` node will be created based on the **Red Hat Enterprise Linux 8.4 Update KVM Guest Image** ([rhel-8.4-x86_64-kvm.qcow2](https://access.redhat.com/downloads/content/479/ver=/rhel---8/8.4/x86_64/product-software)).

To customize `cloud-user` password, you need the `cloud-init` configuration iso file [rhel-cloud-init.iso](https://gitlab.com/neyder/rhel-cloud-init/-/raw/master/rhel-cloud-init.iso).

**Download** those images and place them in the ***storage*** folder inside the working directory.

### Install ansible

```bash
sudo yum install ansible
```

### Test user and ansible installation

```bash
ansible local -m ping
```

```
BECOME password:
workstation | SUCCESS => {
    "changed": false,
    "ping": "pong"
}

```

### For KDE users

If you are running *KDE*, make sure **Klipper** is enabled (right click the expand arrow of your system tray > Configure System Tray... > Entries > Make sure Clipboard is not set to 'Disabled').

Also, before running the playbook, in a second terminal run:

```bash
sudo klipper
```

Or else you will end up with a failure similar to this one:

```
TASK [VIRTUALBMC - Ensure node exists] ********************************************************************************************
failed: [workstation] (item={'cmd': "vbmc list 2>/dev/null | awk '/undercloud/ {print $4,$8}'", 'stdout': '', 'stderr': '', 'rc': 0, 'start': '2021-12-08 13:51:21.755357', 'end': '2021-12-08 13:51:22.069128', 'delta': '0:00:00.313771', 'changed': False, 'invocation': {'module_args': {'_raw_params': "vbmc list 2>/dev/null | awk '/undercloud/ {print $4,$8}'", '_uses_shell': True, 'warn': True, 'stdin_add_newline': True, 'strip_empty_ends': True, 'argv': None, 'chdir': None, 'executable': None, 'creates': None, 'removes': None, 'stdin': None}}, 'stdout_lines': [], 'stderr_lines': [], 'failed': False, 'item': {'name': 'undercloud', 'title': 'RHOSPVirtLab Undercloud', 'profile': 'undercloud', 'memory': 6291456, 'vcpus': 2, 'bmcport': 6233, 'mac': '0c:1f:0d:11:00', 'disk_size': 107374182400, 'backing_store': 'rhel-8.2-x86_64-kvm.qcow2', 'cdrom': 'rhel-cloud-init.iso', 'nics': {'RHOSPVirtLab_ctlplane': '', 'RHOSPVirtLab_management': '192.168.250.10'}}, 'ansible_loop_var': 'item'}) => {"ansible_loop_var": "item", "changed": true, "cmd": ["vbmc", "add", "--username", "admin", "--password", "admin", "--address", "192.168.250.1", "--port", "6233", "undercloud"], "delta": "0:00:00.306814", "end": "2021-12-08 13:51:23.920380", "item": {"ansible_loop_var": "item", "changed": false, "cmd": "vbmc list 2>/dev/null | awk '/undercloud/ {print $4,$8}'", "delta": "0:00:00.313771", "end": "2021-12-08 13:51:22.069128", "failed": false, "invocation": {"module_args": {"_raw_params": "vbmc list 2>/dev/null | awk '/undercloud/ {print $4,$8}'", "_uses_shell": true, "argv": null, "chdir": null, "creates": null, "executable": null, "removes": null, "stdin": null, "stdin_add_newline": true, "strip_empty_ends": true, "warn": true}}, "item": {"backing_store": "rhel-8.2-x86_64-kvm.qcow2", "bmcport": 6233, "cdrom": "rhel-cloud-init.iso", "disk_size": 107374182400, "mac": "0c:1f:0d:11:00", "memory": 6291456, "name": "undercloud", "nics": {"RHOSPVirtLab_ctlplane": "", "RHOSPVirtLab_management": "192.168.250.10"}, "profile": "undercloud", "title": "RHOSPVirtLab Undercloud", "vcpus": 2}, "rc": 0, "start": "2021-12-08 13:51:21.755357", "stderr": "", "stderr_lines": [], "stdout": "", "stdout_lines": []}, "msg": "non-zero return code", "rc": 1, "start": "2021-12-08 13:51:23.613566", "stderr": "Service 'org.kde.klipper' does not exist.\nTraceback (most recent call last):\n  File \"/usr/bin/vbmc\", line 6, in <module>\n    from virtualbmc.cmd.vbmc import main\n  File \"/usr/lib/python3.9/site-packages/virtualbmc/cmd/vbmc.py\", line 17, in <module>\n    from cliff.app import App\n  File \"/usr/local/lib/python3.9/site-packages/cliff/app.py\", line 23, in <module>\n    import cmd2\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/__init__.py\", line 55, in <module>\n    from .cmd2 import Cmd\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/cmd2.py\", line 85, in <module>\n    from .clipboard import (\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/clipboard.py\", line 19, in <module>\n    _ = pyperclip.paste()\n  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 681, in lazy_load_stub_paste\n    return paste()\n  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 301, in paste_klipper\n    assert len(clipboardContents) > 0\nAssertionError", "stderr_lines": ["Service 'org.kde.klipper' does not exist.", "Traceback (most recent call last):", "  File \"/usr/bin/vbmc\", line 6, in <module>", "    from virtualbmc.cmd.vbmc import main", "  File \"/usr/lib/python3.9/site-packages/virtualbmc/cmd/vbmc.py\", line 17, in <module>", "    from cliff.app import App", "  File \"/usr/local/lib/python3.9/site-packages/cliff/app.py\", line 23, in <module>", "    import cmd2", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/__init__.py\", line 55, in <module>", "    from .cmd2 import Cmd", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/cmd2.py\", line 85, in <module>", "    from .clipboard import (", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/clipboard.py\", line 19, in <module>", "    _ = pyperclip.paste()", "  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 681, in lazy_load_stub_paste", "    return paste()", "  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 301, in paste_klipper", "    assert len(clipboardContents) > 0", "AssertionError"], "stdout": "", "stdout_lines": []}
failed: [workstation] (item={'cmd': "vbmc list 2>/dev/null | awk '/controller0/ {print $4,$8}'", 'stdout': '', 'stderr': '', 'rc': 0, 'start': '2021-12-08 13:51:22.221169', 'end': '2021-12-08 13:51:22.525946', 'delta': '0:00:00.304777', 'changed': False, 'invocation': {'module_args': {'_raw_params': "vbmc list 2>/dev/null | awk '/controller0/ {print $4,$8}'", '_uses_shell': True, 'warn': True, 'stdin_add_newline': True, 'strip_empty_ends': True, 'argv': None, 'chdir': None, 'executable': None, 'creates': None, 'removes': None, 'stdin': None}}, 'stdout_lines': [], 'stderr_lines': [], 'failed': False, 'item': {'name': 'controller0', 'title': 'RHOSPVirtLab Controller 0', 'profile': 'control', 'memory': 8388608, 'vcpus': 2, 'bmcport': 6230, 'mac': '0c:1f:0d:11:01', 'disk_size': 53687091200, 'backing_store': '', 'cdrom': '', 'nics': {'RHOSPVirtLab_ctlplane': '', 'RHOSPVirtLab_storage': '', 'RHOSPVirtLab_storage_mgmt': '', 'RHOSPVirtLab_internal_api': '', 'RHOSPVirtLab_tenant': '', 'RHOSPVirtLab_external': ''}}, 'ansible_loop_var': 'item'}) => {"ansible_loop_var": "item", "changed": true, "cmd": ["vbmc", "add", "--username", "admin", "--password", "admin", "--address", "192.168.250.1", "--port", "6230", "controller0"], "delta": "0:00:00.311453", "end": "2021-12-08 13:51:24.388092", "item": {"ansible_loop_var": "item", "changed": false, "cmd": "vbmc list 2>/dev/null | awk '/controller0/ {print $4,$8}'", "delta": "0:00:00.304777", "end": "2021-12-08 13:51:22.525946", "failed": false, "invocation": {"module_args": {"_raw_params": "vbmc list 2>/dev/null | awk '/controller0/ {print $4,$8}'", "_uses_shell": true, "argv": null, "chdir": null, "creates": null, "executable": null, "removes": null, "stdin": null, "stdin_add_newline": true, "strip_empty_ends": true, "warn": true}}, "item": {"backing_store": "", "bmcport": 6230, "cdrom": "", "disk_size": 53687091200, "mac": "0c:1f:0d:11:01", "memory": 8388608, "name": "controller0", "nics": {"RHOSPVirtLab_ctlplane": "", "RHOSPVirtLab_external": "", "RHOSPVirtLab_internal_api": "", "RHOSPVirtLab_storage": "", "RHOSPVirtLab_storage_mgmt": "", "RHOSPVirtLab_tenant": ""}, "profile": "control", "title": "RHOSPVirtLab Controller 0", "vcpus": 2}, "rc": 0, "start": "2021-12-08 13:51:22.221169", "stderr": "", "stderr_lines": [], "stdout": "", "stdout_lines": []}, "msg": "non-zero return code", "rc": 1, "start": "2021-12-08 13:51:24.076639", "stderr": "Service 'org.kde.klipper' does not exist.\nTraceback (most recent call last):\n  File \"/usr/bin/vbmc\", line 6, in <module>\n    from virtualbmc.cmd.vbmc import main\n  File \"/usr/lib/python3.9/site-packages/virtualbmc/cmd/vbmc.py\", line 17, in <module>\n    from cliff.app import App\n  File \"/usr/local/lib/python3.9/site-packages/cliff/app.py\", line 23, in <module>\n    import cmd2\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/__init__.py\", line 55, in <module>\n    from .cmd2 import Cmd\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/cmd2.py\", line 85, in <module>\n    from .clipboard import (\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/clipboard.py\", line 19, in <module>\n    _ = pyperclip.paste()\n  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 681, in lazy_load_stub_paste\n    return paste()\n  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 301, in paste_klipper\n    assert len(clipboardContents) > 0\nAssertionError", "stderr_lines": ["Service 'org.kde.klipper' does not exist.", "Traceback (most recent call last):", "  File \"/usr/bin/vbmc\", line 6, in <module>", "    from virtualbmc.cmd.vbmc import main", "  File \"/usr/lib/python3.9/site-packages/virtualbmc/cmd/vbmc.py\", line 17, in <module>", "    from cliff.app import App", "  File \"/usr/local/lib/python3.9/site-packages/cliff/app.py\", line 23, in <module>", "    import cmd2", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/__init__.py\", line 55, in <module>", "    from .cmd2 import Cmd", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/cmd2.py\", line 85, in <module>", "    from .clipboard import (", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/clipboard.py\", line 19, in <module>", "    _ = pyperclip.paste()", "  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 681, in lazy_load_stub_paste", "    return paste()", "  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 301, in paste_klipper", "    assert len(clipboardContents) > 0", "AssertionError"], "stdout": "", "stdout_lines": []}
failed: [workstation] (item={'cmd': "vbmc list 2>/dev/null | awk '/compute0/ {print $4,$8}'", 'stdout': '', 'stderr': '', 'rc': 0, 'start': '2021-12-08 13:51:22.668134', 'end': '2021-12-08 13:51:22.958017', 'delta': '0:00:00.289883', 'changed': False, 'invocation': {'module_args': {'_raw_params': "vbmc list 2>/dev/null | awk '/compute0/ {print $4,$8}'", '_uses_shell': True, 'warn': True, 'stdin_add_newline': True, 'strip_empty_ends': True, 'argv': None, 'chdir': None, 'executable': None, 'creates': None, 'removes': None, 'stdin': None}}, 'stdout_lines': [], 'stderr_lines': [], 'failed': False, 'item': {'name': 'compute0', 'title': 'RHOSPVirtLab Compute 0', 'profile': 'compute', 'memory': 6291456, 'vcpus': 4, 'bmcport': 6231, 'mac': '0c:1f:0d:11:02', 'disk_size': 53687091200, 'backing_store': '', 'cdrom': '', 'nics': {'RHOSPVirtLab_ctlplane': '', 'RHOSPVirtLab_storage': '', 'RHOSPVirtLab_storage_mgmt': '', 'RHOSPVirtLab_internal_api': '', 'RHOSPVirtLab_tenant': '', 'RHOSPVirtLab_external': ''}}, 'ansible_loop_var': 'item'}) => {"ansible_loop_var": "item", "changed": true, "cmd": ["vbmc", "add", "--username", "admin", "--password", "admin", "--address", "192.168.250.1", "--port", "6231", "compute0"], "delta": "0:00:00.318383", "end": "2021-12-08 13:51:24.859400", "item": {"ansible_loop_var": "item", "changed": false, "cmd": "vbmc list 2>/dev/null | awk '/compute0/ {print $4,$8}'", "delta": "0:00:00.289883", "end": "2021-12-08 13:51:22.958017", "failed": false, "invocation": {"module_args": {"_raw_params": "vbmc list 2>/dev/null | awk '/compute0/ {print $4,$8}'", "_uses_shell": true, "argv": null, "chdir": null, "creates": null, "executable": null, "removes": null, "stdin": null, "stdin_add_newline": true, "strip_empty_ends": true, "warn": true}}, "item": {"backing_store": "", "bmcport": 6231, "cdrom": "", "disk_size": 53687091200, "mac": "0c:1f:0d:11:02", "memory": 6291456, "name": "compute0", "nics": {"RHOSPVirtLab_ctlplane": "", "RHOSPVirtLab_external": "", "RHOSPVirtLab_internal_api": "", "RHOSPVirtLab_storage": "", "RHOSPVirtLab_storage_mgmt": "", "RHOSPVirtLab_tenant": ""}, "profile": "compute", "title": "RHOSPVirtLab Compute 0", "vcpus": 4}, "rc": 0, "start": "2021-12-08 13:51:22.668134", "stderr": "", "stderr_lines": [], "stdout": "", "stdout_lines": []}, "msg": "non-zero return code", "rc": 1, "start": "2021-12-08 13:51:24.541017", "stderr": "Service 'org.kde.klipper' does not exist.\nTraceback (most recent call last):\n  File \"/usr/bin/vbmc\", line 6, in <module>\n    from virtualbmc.cmd.vbmc import main\n  File \"/usr/lib/python3.9/site-packages/virtualbmc/cmd/vbmc.py\", line 17, in <module>\n    from cliff.app import App\n  File \"/usr/local/lib/python3.9/site-packages/cliff/app.py\", line 23, in <module>\n    import cmd2\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/__init__.py\", line 55, in <module>\n    from .cmd2 import Cmd\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/cmd2.py\", line 85, in <module>\n    from .clipboard import (\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/clipboard.py\", line 19, in <module>\n    _ = pyperclip.paste()\n  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 681, in lazy_load_stub_paste\n    return paste()\n  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 301, in paste_klipper\n    assert len(clipboardContents) > 0\nAssertionError", "stderr_lines": ["Service 'org.kde.klipper' does not exist.", "Traceback (most recent call last):", "  File \"/usr/bin/vbmc\", line 6, in <module>", "    from virtualbmc.cmd.vbmc import main", "  File \"/usr/lib/python3.9/site-packages/virtualbmc/cmd/vbmc.py\", line 17, in <module>", "    from cliff.app import App", "  File \"/usr/local/lib/python3.9/site-packages/cliff/app.py\", line 23, in <module>", "    import cmd2", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/__init__.py\", line 55, in <module>", "    from .cmd2 import Cmd", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/cmd2.py\", line 85, in <module>", "    from .clipboard import (", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/clipboard.py\", line 19, in <module>", "    _ = pyperclip.paste()", "  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 681, in lazy_load_stub_paste", "    return paste()", "  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 301, in paste_klipper", "    assert len(clipboardContents) > 0", "AssertionError"], "stdout": "", "stdout_lines": []}
failed: [workstation] (item={'cmd': "vbmc list 2>/dev/null | awk '/compute1/ {print $4,$8}'", 'stdout': '', 'stderr': '', 'rc': 0, 'start': '2021-12-08 13:51:23.105613', 'end': '2021-12-08 13:51:23.415454', 'delta': '0:00:00.309841', 'changed': False, 'invocation': {'module_args': {'_raw_params': "vbmc list 2>/dev/null | awk '/compute1/ {print $4,$8}'", '_uses_shell': True, 'warn': True, 'stdin_add_newline': True, 'strip_empty_ends': True, 'argv': None, 'chdir': None, 'executable': None, 'creates': None, 'removes': None, 'stdin': None}}, 'stdout_lines': [], 'stderr_lines': [], 'failed': False, 'item': {'name': 'compute1', 'title': 'RHOSPVirtLab Compute 1', 'profile': 'compute', 'memory': 6291456, 'vcpus': 4, 'bmcport': 6232, 'mac': '0c:1f:0d:11:03', 'disk_size': 53687091200, 'backing_store': '', 'cdrom': '', 'nics': {'RHOSPVirtLab_ctlplane': '', 'RHOSPVirtLab_storage': '', 'RHOSPVirtLab_storage_mgmt': '', 'RHOSPVirtLab_internal_api': '', 'RHOSPVirtLab_tenant': '', 'RHOSPVirtLab_external': ''}}, 'ansible_loop_var': 'item'}) => {"ansible_loop_var": "item", "changed": true, "cmd": ["vbmc", "add", "--username", "admin", "--password", "admin", "--address", "192.168.250.1", "--port", "6232", "compute1"], "delta": "0:00:00.299091", "end": "2021-12-08 13:51:25.312021", "item": {"ansible_loop_var": "item", "changed": false, "cmd": "vbmc list 2>/dev/null | awk '/compute1/ {print $4,$8}'", "delta": "0:00:00.309841", "end": "2021-12-08 13:51:23.415454", "failed": false, "invocation": {"module_args": {"_raw_params": "vbmc list 2>/dev/null | awk '/compute1/ {print $4,$8}'", "_uses_shell": true, "argv": null, "chdir": null, "creates": null, "executable": null, "removes": null, "stdin": null, "stdin_add_newline": true, "strip_empty_ends": true, "warn": true}}, "item": {"backing_store": "", "bmcport": 6232, "cdrom": "", "disk_size": 53687091200, "mac": "0c:1f:0d:11:03", "memory": 6291456, "name": "compute1", "nics": {"RHOSPVirtLab_ctlplane": "", "RHOSPVirtLab_external": "", "RHOSPVirtLab_internal_api": "", "RHOSPVirtLab_storage": "", "RHOSPVirtLab_storage_mgmt": "", "RHOSPVirtLab_tenant": ""}, "profile": "compute", "title": "RHOSPVirtLab Compute 1", "vcpus": 4}, "rc": 0, "start": "2021-12-08 13:51:23.105613", "stderr": "", "stderr_lines": [], "stdout": "", "stdout_lines": []}, "msg": "non-zero return code", "rc": 1, "start": "2021-12-08 13:51:25.012930", "stderr": "Service 'org.kde.klipper' does not exist.\nTraceback (most recent call last):\n  File \"/usr/bin/vbmc\", line 6, in <module>\n    from virtualbmc.cmd.vbmc import main\n  File \"/usr/lib/python3.9/site-packages/virtualbmc/cmd/vbmc.py\", line 17, in <module>\n    from cliff.app import App\n  File \"/usr/local/lib/python3.9/site-packages/cliff/app.py\", line 23, in <module>\n    import cmd2\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/__init__.py\", line 55, in <module>\n    from .cmd2 import Cmd\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/cmd2.py\", line 85, in <module>\n    from .clipboard import (\n  File \"/usr/local/lib/python3.9/site-packages/cmd2/clipboard.py\", line 19, in <module>\n    _ = pyperclip.paste()\n  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 681, in lazy_load_stub_paste\n    return paste()\n  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 301, in paste_klipper\n    assert len(clipboardContents) > 0\nAssertionError", "stderr_lines": ["Service 'org.kde.klipper' does not exist.", "Traceback (most recent call last):", "  File \"/usr/bin/vbmc\", line 6, in <module>", "    from virtualbmc.cmd.vbmc import main", "  File \"/usr/lib/python3.9/site-packages/virtualbmc/cmd/vbmc.py\", line 17, in <module>", "    from cliff.app import App", "  File \"/usr/local/lib/python3.9/site-packages/cliff/app.py\", line 23, in <module>", "    import cmd2", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/__init__.py\", line 55, in <module>", "    from .cmd2 import Cmd", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/cmd2.py\", line 85, in <module>", "    from .clipboard import (", "  File \"/usr/local/lib/python3.9/site-packages/cmd2/clipboard.py\", line 19, in <module>", "    _ = pyperclip.paste()", "  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 681, in lazy_load_stub_paste", "    return paste()", "  File \"/usr/local/lib/python3.9/site-packages/pyperclip/__init__.py\", line 301, in paste_klipper", "    assert len(clipboardContents) > 0", "AssertionError"], "stdout": "", "stdout_lines": []}

PLAY RECAP ************************************************************************************************************************
workstation                : ok=22   changed=9    unreachable=0    failed=1    skipped=7    rescued=0    ignored=0  
```

### Install requirements

```bash
ansible-galaxy collection install -r requirements.yml
ansible-galaxy install -r requirements.yml
```

## Create a vault for credentials

You need to create a vault file to store your Red Hat Subscription credentials. To do that, execute the following command:

```bash
ansible-vault create vault_credentials.yaml
```

You will write the credentials in the following format:

```yml
rh_username: '<USERNAME>'
rh_password: '<PASSWORD>'
```

## Clean the installation

To start/restart the installation from scratch, a playbook is provided to clean everything in the local machine. Every progress in the lab will be erased. Please **be careful** with this command:

```bash
ansible-playbook clean.yml
```

## Execute the Ansible Playbook

Execute the playbook with the following command (you will be prompted for the user password and the vault password):

```bash
ansible-playbook --ask-vault-pass playbook.yml
```

The playbook sets up the following environment:

![Overview](images/overview.png)

![Network diagram](images/network_diagram.png)

### Customizing the environment

If you want to customize the default environment created by the playbook, you need to edit the files:

- vars/networks.yml
- vars/vms.yml

## Last steps

As the `undercloud` installation and `overcloud` deploy are tasks that last longer and require attention due to possible failures, they need to be executed manually. To do that, login to the `undercloud`:

```bash
ssh stack@undercloud
```

### Install the undercloud

Execute the following command:

```bash
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

Load the `overcloud` images to openstack:

```bash
source /home/stack/stackrc
openstack overcloud image upload --image-path /home/stack/images/
```

List images:

```bash
openstack image list --fit-width
```

Import the bremetal nodes:

```bash
source /home/stack/stackrc
openstack overcloud node import --validate-only /home/stack/templates/instackenv.yaml
openstack overcloud node import /home/stack/templates/instackenv.yaml
openstack baremetal node list
```

Run validations (you can ignore the `undercloud-neutron-sanity-check` `FAILED`):

```bash
openstack tripleo validator run --group pre-introspection
```

Introspect the nodes:

```bash
openstack overcloud node introspect --all-manageable --provide
```

After the process finishes, the nodes must be in `available` state:

```bash
openstack baremetal node list
```

List the profiles to check if they match the configuration:

```bash
openstack overcloud profiles list
```

Generate the roles file:

```bash
source /home/stack/stackrc
openstack overcloud roles generate \
--roles-path /usr/share/openstack-tripleo-heat-templates/roles \
-o /home/stack/templates/roles_data.yaml \
Controller Compute
```

Prepare the images for containers:

```bash
source /home/stack/stackrc
sudo openstack tripleo container image prepare -e /home/stack/templates/containers-prepare-parameter.yaml --output-env-file /home/stack/templates/overcloud-images.yaml
```

### Deploy the overcloud

Execute the deploy command with all the templates and environment files:

```bash
source /home/stack/stackrc
openstack overcloud deploy \
--log-file overcloud_deployment.log \
--timeout 120 \
--templates /usr/share/openstack-tripleo-heat-templates/ \
--stack overcloud \
--ntp-server 0.pool.ntp.org,1.pool.ntp.org,2.pool.ntp.org,3.pool.ntp.org \
-r /home/stack/templates/roles_data.yaml \
-n /home/stack/templates/network_data.yaml \
-e /home/stack/templates/node-info.yaml \
-e /home/stack/templates/containers-prepare-parameter.yaml \
-e /home/stack/templates/overcloud-images.yaml \
-e /home/stack/templates/custom-overcloud.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/enable-swap.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/network-isolation.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/network-environment.yaml \
-e /usr/share/openstack-tripleo-heat-templates/environments/net-multiple-nics.yaml
```

The output should end with the following:

```
Ansible passed.
Overcloud configuration completed.
Overcloud Endpoint: http://10.0.0.254:5000
Overcloud Horizon Dashboard URL: http://10.0.0.254:80/dashboard
Overcloud rc file: /home/stack/overcloudrc
Overcloud Deployed without error
```

Analize the Overcloud rc file to take note of the admin password:

```bash
grep PASSWORD overcloudrc
```

```
export OS_PASSWORD=XXXXXXXXXXXXXX
```

### Post deploy configurations

#### Create a domain and a project

```
source /home/stack/overcloudrc
openstack domain create RHOSPVirtLab
openstack project create --domain RHOSPVirtLab test-project
```

#### Create domain users

```
source /home/stack/overcloudrc
openstack user create --domain RHOSPVirtLab --project test-project --project-domain RHOSPVirtLab --password-prompt --description "Test project admin" test-admin
```
(Choose a password for the test-admin user)

Assign administration roles:

```
openstack role add --domain RHOSPVirtLab --user test-admin --user-domain RHOSPVirtLab admin
openstack role add --project test-project --user test-admin --user-domain RHOSPVirtLab admin
```

### Create a provider network

```
source /home/stack/overcloudrc
openstack network create --share --external --provider-network-type flat --provider-physical-network datacentre default-provider
openstack subnet create --subnet-range 10.0.0.0/24 --no-dhcp --gateway 10.0.0.1 --network default-provider --allocation-pool start=10.0.0.100,end=10.0.0.250 default-provider-subnet
```

### Open dashboard

From a web browser, open the Overcloud Horizon Dashboard URL ([http://10.0.0.254:80/dashboard](http://10.0.0.254:80/dashboard)) and login to the domain **RHOSPVirtLab** as **test-admin** using the password you configured.

![Dashboard](images/dashboard.png)

![Hypervisors](images/hypervisors.png)

#### Requirements for instances

In order to be able to boot some instances with public access:

 * Create a tenant network.
 * Create a router. Set the `default-provider` as external network. Attach a port to the tenant network with the default gateway IP.
 * Assign floating IPs to the project.
 * Create some flavors.
 * Upload some images.
