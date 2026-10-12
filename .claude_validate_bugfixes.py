#!/usr/bin/env python3
import re
import sys

import yaml

try:
    import jinja2
except ImportError:
    jinja2 = None


def make_env():
    """A jinja2.Environment with the Ansible-only filters our templates rely on
    (these come from ansible-core's filter plugins, not plain Jinja2)."""
    env = jinja2.Environment()
    env.filters["intersect"] = lambda a, b: [x for x in a if x in b]
    env.filters["difference"] = lambda a, b: [x for x in a if x not in b]
    env.filters["to_yaml"] = lambda data, **kw: yaml.dump(data, allow_unicode=True, default_flow_style=False, **kw)
    env.filters["to_nice_yaml"] = lambda data, indent=4, **kw: yaml.dump(
        data, indent=indent, allow_unicode=True, default_flow_style=False, **kw
    )
    return env


# 0. Diagnostic: confirm this control node's actual Ansible/Jinja2 understands
#    indent(..., first=True). Older Jinja2 (pre-2.10) named this kwarg
#    `indentfirst` instead of `first`; if this control node has an old Jinja2,
#    first=True would be rejected (loudly, as a TypeError) rather than silently
#    ignored - this check surfaces that before you dig further into a real
#    ansible-playbook run.
print("=== Diagnostic: Jinja2/Ansible indent(first=True) support on this control node ===")
try:
    import subprocess
    result = subprocess.run(["ansible", "--version"], capture_output=True, text=True, timeout=10)
    print("  ansible --version:")
    for line in result.stdout.splitlines()[:5]:
        print(f"    {line}")
except Exception as e:
    print(f"  ansible --version: could not run ({e})")

if jinja2 is None:
    print("  jinja2 not importable in this Python - cannot run the live indent() check")
else:
    print(f"  jinja2.__version__ = {jinja2.__version__}")
    try:
        env = jinja2.Environment()
        rendered = env.from_string("{{ ('line1\\nline2' | indent(width=2, first=True)) }}").render()
        lines = rendered.split("\n")
        if lines[0].startswith("  "):
            print(f"  OK   indent(width=2, first=True) indents the first line on this Jinja2: {rendered!r}")
        else:
            print(f"  FAIL indent(width=2, first=True) did NOT indent the first line on this Jinja2: {rendered!r}")
    except TypeError as e:
        print(f"  FAIL this Jinja2 rejects the 'first' keyword argument entirely: {e}")
        print("       (older Jinja2 used 'indentfirst' instead of 'first' - this would explain the bug)")
    except Exception as e:
        print(f"  FAIL unexpected error testing indent(first=True): {e}")
print()

FILES = [
    "roles/RHOSP-kubevirt-infra/defaults/main.yml",
    "vars/options.yml",
    "vars/machines.yml",
    "roles/RHOSP-virt-infra/tasks/checks.yml",
    "roles/RHOSP-undercloud/tasks/main.yml",
    "roles/RHOSP-kubevirt-infra/tasks/main.yml",
    "roles/RHOSP-undercloud/vars/main.yml",
    "roles/RHOSP-undercloud/tasks/overcloud.yml",
    "roles/RHOSP-undercloud/tasks/leafs.yml",
    "roles/RHOSP-virt-infra/tasks/clean_libvirt_storage.yml",
    "roles/RHOSP-kubevirt-infra/tasks/create_kubernetes_resources.yml",
    "roles/RHOSP-virt-infra/tasks/create_virtualbmc.yml",
    "roles/RHOSP-undercloud/tasks/subscription.yml",
    "roles/RHOSP-virt-infra/tasks/create_libvirt_cloud_init.yml",
    "roles/RHOSP-virt-infra/tasks/clean_network_profiles.yml",
    "roles/RHOSP-virt-infra/tasks/configure_firewall.yml",
    "roles/RHOSP-kubevirt-infra/tasks/setup.yml",
    "roles/RHOSP-undercloud/tasks/undercloud-network.yml",
    "roles/RHOSP-undercloud/defaults/main.yml",
    "roles/RHOSP-virt-infra/tasks/create_network_profiles.yml",
]

ok = True

# 1. Plain YAML syntax check for every file touched by a fix.
for f in FILES:
    try:
        with open(f) as fh:
            yaml.safe_load(fh)
        print(f"  OK   {f}")
    except Exception as e:
        ok = False
        print(f"  FAIL {f}: {e}")

# 2. Logic check for the "trunking NIC without libvirt machines" guard added to
#    RHOSP-virt-infra/tasks/checks.yml: render the real `trunking_leafs` Jinja
#    template (pulled straight from the YAML, not reimplemented) against
#    synthetic `leafs` fixtures and confirm it flags/ignores the right leaves.
CHECKS_FILE = "roles/RHOSP-virt-infra/tasks/checks.yml"
TASK_NAME = (
    "CHECKS - Fail if a leaf trunks a NIC into a hypervisor bridge "
    "without any libvirt machines in the deployment"
)


def leaf(name, ctlplane_interface=None, additional_bridges=None):
    return {
        "name": name,
        "ctlplane_bridge": {"interface": ctlplane_interface},
        "additional_bridges": additional_bridges or [],
    }


def render_trunking_leafs(template_src, leafs):
    env = make_env()
    rendered = env.from_string(template_src).render(leafs=leafs)
    return yaml.safe_load(rendered) or []


if jinja2 is None:
    print("  SKIP trunking_leafs logic tests: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(CHECKS_FILE) as fh:
            tasks = yaml.safe_load(fh)
        task = next(t for t in tasks if t.get("name") == TASK_NAME)
        template_src = task["vars"]["trunking_leafs"]

        fixtures = [
            ("no trunking anywhere", [leaf("overcloud")], []),
            ("ctlplane_bridge.interface set", [leaf("overcloud", ctlplane_interface="eno2")], ["overcloud"]),
            (
                "additional_bridges[].interface set",
                [leaf("overcloud", additional_bridges=[{"interface": "eno3"}])],
                ["overcloud"],
            ),
            (
                "additional_bridges[].interface present but null",
                [leaf("overcloud", additional_bridges=[{"interface": None}])],
                [],
            ),
            (
                "mixed leafs, only one trunked",
                [leaf("overcloud"), leaf("leaf1", ctlplane_interface="eno4")],
                ["leaf1"],
            ),
        ]

        for label, leafs, expected in fixtures:
            result = render_trunking_leafs(template_src, leafs)
            if result == expected:
                print(f"  OK   trunking_leafs logic: {label}")
            else:
                ok = False
                print(f"  FAIL trunking_leafs logic: {label}: expected {expected}, got {result}")

        when_clauses = " ".join(task.get("when", []))
        if "libvirt_required" in when_clauses:
            print("  OK   checks.yml: new task's `when` references libvirt_required")
        else:
            ok = False
            print("  FAIL checks.yml: new task's `when` no longer references libvirt_required")

    except StopIteration:
        ok = False
        print(f"  FAIL {CHECKS_FILE}: task '{TASK_NAME}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {CHECKS_FILE} logic check: {e}")

# 3. Logic check for the "initial-ceph.conf is never rendered per-DCN-leaf" fix in
#    deploy.sh.j2: render the real template (not a reimplementation) for a DCN leaf
#    with HCI nodes on RHOSP >= 17.1 and confirm it references the shared
#    initial-ceph.conf path, never a per-leaf one.
DEPLOY_SH_FILE = "roles/RHOSP-undercloud/templates/deploy.sh.j2"

if jinja2 is None:
    print("  SKIP deploy.sh.j2 logic test: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(DEPLOY_SH_FILE) as fh:
            template_src = fh.read()

        zero_roles = {
            "CephStorage": 0,
            "CephAll": 0,
            "ComputeHCI": 0,
            "DistributedComputeHCI": 0,
            "DistributedComputeHCIScaleOut": 0,
        }
        hci_roles = dict(zero_roles, ComputeHCI=1)

        context = {
            "leaf": {"name": "leaf1"},
            "default_leaf": {"name": "overcloud"},
            "dcn_leafs": [{"name": "leaf1"}],
            "roles_count": {"overcloud": zero_roles, "leaf1": hci_roles},
            "RHOSP_version": 17.1,
            "ntp_servers": ["0.pool.ntp.org"],
            "deployed_server": {"overcloud": False, "leaf1": False},
            "deployment_environment": [],
        }

        env = make_env()
        rendered = env.from_string(template_src).render(**context)

        if "--config /home/stack/templates/initial-ceph.conf" in rendered:
            print("  OK   deploy.sh.j2: DCN leaf with HCI references the shared initial-ceph.conf path")
        else:
            ok = False
            print("  FAIL deploy.sh.j2: rendered script does not reference the shared initial-ceph.conf path")

        if "/home/stack/templates/leaf1/initial-ceph.conf" in rendered:
            ok = False
            print("  FAIL deploy.sh.j2: rendered script still references the never-rendered per-leaf initial-ceph.conf")
        else:
            print("  OK   deploy.sh.j2: no reference to a per-leaf initial-ceph.conf")

    except Exception as e:
        ok = False
        print(f"  FAIL {DEPLOY_SH_FILE} logic check: {e}")

# 4. Logic check for the "repo verification only checks the last repo" fix in
#    RHOSP-undercloud/tasks/main.yml: compile the real `when` expression (pulled
#    straight from the YAML) and evaluate it against synthetic
#    `subscription-manager repos --list-enabled` outputs.
UNDERCLOUD_MAIN_FILE = "roles/RHOSP-undercloud/tasks/main.yml"
FALLBACK_TASK_NAME = "REPOSITORIES - Enable the needed repositories only (raw fallback)"

UNDERCLOUD_REPOS_171 = [
    "rhel-9-for-x86_64-baseos-eus-rpms",
    "rhel-9-for-x86_64-appstream-eus-rpms",
    "rhel-9-for-x86_64-highavailability-eus-rpms",
    "openstack-17.1-for-rhel-9-x86_64-rpms",
    "fast-datapath-for-rhel-9-x86_64-rpms",
]
UNDERCLOUD_REPOS_162 = [
    "rhel-8-for-x86_64-baseos-rpms",
    "rhel-8-for-x86_64-appstream-rpms",
    "rhel-8-for-x86_64-highavailability-rpms",
    "ansible-2.9-for-rhel-8-x86_64-rpms",
    "openstack-16.2-for-rhel-8-x86_64-rpms",
    "fast-datapath-for-rhel-8-x86_64-rpms",
    "rhceph-4-tools-for-rhel-8-x86_64-rpms",
]


def stdout_for(repos, missing=()):
    enabled = [r for r in repos if r not in missing]
    return "\n".join(f"Repo ID:   {r}" for r in enabled)


if jinja2 is None:
    print("  SKIP repo verification logic tests: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(UNDERCLOUD_MAIN_FILE) as fh:
            tasks = yaml.safe_load(fh)
        task = next(t for t in tasks if t.get("name") == FALLBACK_TASK_NAME)
        when_expr = task["when"]

        env = make_env()
        compiled = env.compile_expression(when_expr)

        fixtures = [
            (
                "17.1: all repos enabled",
                17.1, UNDERCLOUD_REPOS_171, stdout_for(UNDERCLOUD_REPOS_171), 0,
                False,
            ),
            (
                "17.1: rc != 0",
                17.1, UNDERCLOUD_REPOS_171, stdout_for(UNDERCLOUD_REPOS_171), 1,
                True,
            ),
            (
                "17.1: OpenStack repo missing, last repo (fast-datapath) present",
                17.1, UNDERCLOUD_REPOS_171,
                stdout_for(UNDERCLOUD_REPOS_171, missing=["openstack-17.1-for-rhel-9-x86_64-rpms"]), 0,
                True,
            ),
            (
                "17.1: last repo (fast-datapath) missing",
                17.1, UNDERCLOUD_REPOS_171,
                stdout_for(UNDERCLOUD_REPOS_171, missing=["fast-datapath-for-rhel-9-x86_64-rpms"]), 0,
                True,
            ),
            (
                "16.2: OpenStack repo missing, last repo (rhceph-4-tools) present",
                16.2, UNDERCLOUD_REPOS_162,
                stdout_for(UNDERCLOUD_REPOS_162, missing=["openstack-16.2-for-rhel-8-x86_64-rpms"]), 0,
                True,
            ),
        ]

        for label, rhosp_version, repos, stdout, rc, expected in fixtures:
            context = {
                "repos_enabled": {"rc": rc, "stdout": stdout},
                "RHOSP_version": rhosp_version,
                "RHOSP_version_supported": {rhosp_version: {"undercloud_repos": repos}},
            }
            result = bool(compiled(**context))
            if result == expected:
                print(f"  OK   repo verification logic: {label}")
            else:
                ok = False
                print(f"  FAIL repo verification logic: {label}: expected {expected}, got {result}")

    except StopIteration:
        ok = False
        print(f"  FAIL {UNDERCLOUD_MAIN_FILE}: task '{FALLBACK_TASK_NAME}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {UNDERCLOUD_MAIN_FILE} logic check: {e}")

# 5. Logic check for the "KubeVirt External network missing gateway" fix in
#    RHOSP-kubevirt-infra/defaults/main.yml: parse the real leafs data and replicate
#    the exact Jinja filter chain used by tasks/checks.yml and undercloud.yaml.j2
#    (`networks | selectattr('subnet.gateway', 'defined')`) to confirm External is
#    now picked up as a gateway network.
KUBEVIRT_DEFAULTS_FILE = "roles/RHOSP-kubevirt-infra/defaults/main.yml"

if jinja2 is None:
    print("  SKIP External network gateway logic test: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(KUBEVIRT_DEFAULTS_FILE) as fh:
            defaults = yaml.safe_load(fh)
        default_leaf = next(lf for lf in defaults["leafs"] if lf["name"] == "overcloud")
        external = next(n for n in default_leaf["networks"] if n["name"] == "External")

        if "gateway" in external["subnet"]:
            print("  OK   kubevirt defaults: External network subnet has a gateway key")
        else:
            ok = False
            print("  FAIL kubevirt defaults: External network subnet is still missing gateway")

        env = make_env()
        compiled = env.compile_expression(
            "networks | selectattr('subnet.gateway', 'defined') | map(attribute='name') | list"
        )
        gw_network_names = compiled(networks=default_leaf["networks"])
        if "External" in gw_network_names:
            print("  OK   kubevirt defaults: External is picked up by the gw_networks filter chain")
        else:
            ok = False
            print(f"  FAIL kubevirt defaults: gw_networks filter chain still excludes External: {gw_network_names}")

    except (StopIteration, KeyError) as e:
        ok = False
        print(f"  FAIL {KUBEVIRT_DEFAULTS_FILE}: could not locate overcloud leaf / External network: {e}")
    except Exception as e:
        ok = False
        print(f"  FAIL {KUBEVIRT_DEFAULTS_FILE} logic check: {e}")

# 6. Content check for the "kubevirt cleanup doesn't actually clean up" fix: the
#    debug message must no longer claim resources were already deleted, and must
#    make clear the printed oc delete commands are manual.
KUBEVIRT_MAIN_FILE = "roles/RHOSP-kubevirt-infra/tasks/main.yml"
CLEANUP_TASK_NAME = "KUBERNETES - Display cleanup instructions"

try:
    with open(KUBEVIRT_MAIN_FILE) as fh:
        kubevirt_tasks = yaml.safe_load(fh)
    cleanup_task = next(t for t in kubevirt_tasks if t.get("name") == CLEANUP_TASK_NAME)
    msg = cleanup_task["debug"]["msg"]

    if "have been cleaned up" in msg.lower():
        ok = False
        print(f"  FAIL {KUBEVIRT_MAIN_FILE}: cleanup message still claims resources were already deleted")
    else:
        print(f"  OK   {KUBEVIRT_MAIN_FILE}: cleanup message no longer claims automatic deletion")

    if "does not delete" in msg.lower() or "manually" in msg.lower() or "yourself" in msg.lower():
        print(f"  OK   {KUBEVIRT_MAIN_FILE}: cleanup message makes clear deletion is manual")
    else:
        ok = False
        print(f"  FAIL {KUBEVIRT_MAIN_FILE}: cleanup message no longer makes clear deletion is manual")

except StopIteration:
    ok = False
    print(f"  FAIL {KUBEVIRT_MAIN_FILE}: task '{CLEANUP_TASK_NAME}' not found")
except Exception as e:
    ok = False
    print(f"  FAIL {KUBEVIRT_MAIN_FILE} content check: {e}")

# 7. Content check for the "kubevirt create bullet overclaims automatic creation"
#    fix: the README's `create` bullet must no longer imply the role applies
#    anything to the cluster itself.
KUBEVIRT_README_FILE = "roles/RHOSP-kubevirt-infra/README.md"

try:
    with open(KUBEVIRT_README_FILE) as fh:
        readme = fh.read()

    old_overclaim = "Create KubeVirt resources (VirtualMachines, UserDefinedNetworks, Secrets). Useful with cleanup:True"
    if old_overclaim in readme:
        ok = False
        print(f"  FAIL {KUBEVIRT_README_FILE}: create bullet still overclaims automatic resource creation")
    else:
        print(f"  OK   {KUBEVIRT_README_FILE}: create bullet no longer overclaims automatic creation")

    if "oc apply` commands" in readme and "must run the printed commands yourself" in readme:
        print(f"  OK   {KUBEVIRT_README_FILE}: create bullet clarifies manual `oc apply`")
    else:
        ok = False
        print(f"  FAIL {KUBEVIRT_README_FILE}: create bullet no longer clarifies manual `oc apply`")

except Exception as e:
    ok = False
    print(f"  FAIL {KUBEVIRT_README_FILE} content check: {e}")

# 8. Logic check for the "DCN leaf co-located with the control-plane hypervisor"
#    guard added to RHOSP-undercloud/tasks/main.yml: render the real
#    `shared_hypervisors` Jinja template against synthetic single- and
#    multi-hypervisor fixtures.
UNDERCLOUD_HYPERVISOR_TASK_NAME = "CHECKS - Fail if a DCN leaf shares a hypervisor with the control-plane leaf"

if jinja2 is None:
    print("  SKIP shared_hypervisors logic tests: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(UNDERCLOUD_MAIN_FILE) as fh:
            undercloud_tasks = yaml.safe_load(fh)
        hyp_task = next(t for t in undercloud_tasks if t.get("name") == UNDERCLOUD_HYPERVISOR_TASK_NAME)
        template_src = hyp_task["vars"]["shared_hypervisors"]

        env = make_env()

        def shared_hypervisors(dcn_hypervisor, default_hypervisor):
            rendered = env.from_string(template_src).render(
                dcn_leaf={"hypervisor": dcn_hypervisor},
                default_leaf={"hypervisor": default_hypervisor},
            )
            return yaml.safe_load(rendered) or []

        fixtures = [
            ("no overlap, single hypervisors", "hypervisor1", "localhost", []),
            ("exact match, single hypervisors", "localhost", "localhost", ["localhost"]),
            ("overlap in multi-hypervisor lists", "hypervisor1,localhost", "localhost,hypervisor2", ["localhost"]),
            ("no overlap, multi-hypervisor lists", "hypervisor1,hypervisor2", "localhost,hypervisor3", []),
        ]

        for label, dcn_hyp, default_hyp, expected in fixtures:
            result = shared_hypervisors(dcn_hyp, default_hyp)
            if result == expected:
                print(f"  OK   shared_hypervisors logic: {label}")
            else:
                ok = False
                print(f"  FAIL shared_hypervisors logic: {label}: expected {expected}, got {result}")

    except StopIteration:
        ok = False
        print(f"  FAIL {UNDERCLOUD_MAIN_FILE}: task '{UNDERCLOUD_HYPERVISOR_TASK_NAME}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {UNDERCLOUD_MAIN_FILE} shared_hypervisors check: {e}")

# 9. Checks for the "director images unpacked unconditionally" fix:
#    (a) vars/main.yml's images_directories is now a named dict (ipa/bios/uefi) for
#        17.1 and a dict without uefi for 16.2;
#    (b) the real ironic_provisioned_machines / needs_bios_image / needs_uefi_image
#        Jinja templates, pulled from tasks/main.yml, are rendered against synthetic
#        libvirt_machines/physical_machines fixtures covering pre_provisioned and
#        pm.mode combinations.
UNDERCLOUD_VARS_FILE = "roles/RHOSP-undercloud/vars/main.yml"

try:
    with open(UNDERCLOUD_VARS_FILE) as fh:
        undercloud_vars = yaml.safe_load(fh)
    images_171 = undercloud_vars["RHOSP_version_supported"][17.1]["images_directories"]
    images_162 = undercloud_vars["RHOSP_version_supported"][16.2]["images_directories"]

    if isinstance(images_171, dict) and {"ipa", "bios", "uefi"} <= images_171.keys():
        print(f"  OK   {UNDERCLOUD_VARS_FILE}: 17.1 images_directories has ipa/bios/uefi keys")
    else:
        ok = False
        print(f"  FAIL {UNDERCLOUD_VARS_FILE}: 17.1 images_directories missing expected keys: {images_171}")

    if isinstance(images_162, dict) and {"ipa", "bios"} <= images_162.keys() and "uefi" not in images_162:
        print(f"  OK   {UNDERCLOUD_VARS_FILE}: 16.2 images_directories has ipa/bios keys and no uefi")
    else:
        ok = False
        print(f"  FAIL {UNDERCLOUD_VARS_FILE}: 16.2 images_directories unexpected shape: {images_162}")

except Exception as e:
    ok = False
    print(f"  FAIL {UNDERCLOUD_VARS_FILE} structure check: {e}")

IMAGES_TASK_NAME = "IMAGES - Determine which director images are actually needed"
BIOS_UEFI_TASK_NAME = "IMAGES - Determine BIOS/UEFI image requirements"


def machine(pre_provisioned=None, pm_mode="unset", has_pm=True):
    """pm_mode='unset' means the pm block exists but has no mode key;
    has_pm=False means the pm block is absent entirely (the chained
    dotted-attribute edge case the fix must not crash on)."""
    m = {}
    if pre_provisioned is not None:
        m["pre_provisioned"] = pre_provisioned
    if has_pm:
        m["pm"] = {} if pm_mode == "unset" else {"mode": pm_mode}
    return m


if jinja2 is None:
    print("  SKIP director image requirement logic tests: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(UNDERCLOUD_MAIN_FILE) as fh:
            undercloud_tasks = yaml.safe_load(fh)
        images_task = next(t for t in undercloud_tasks if t.get("name") == IMAGES_TASK_NAME)
        bios_uefi_task = next(t for t in undercloud_tasks if t.get("name") == BIOS_UEFI_TASK_NAME)

        ironic_tmpl = images_task["set_fact"]["ironic_provisioned_machines"]
        ironic_candidates_tmpl = images_task["vars"]["ironic_candidates"]
        bios_tmpl = bios_uefi_task["set_fact"]["needs_bios_image"]
        uefi_tmpl = bios_uefi_task["set_fact"]["needs_uefi_image"]

        env = make_env()

        def compute(libvirt_machines, physical_machines):
            ironic_candidates = yaml.safe_load(
                env.from_string(ironic_candidates_tmpl).render(
                    libvirt_machines=libvirt_machines, physical_machines=physical_machines
                )
            )
            ironic_provisioned = yaml.safe_load(
                env.from_string(ironic_tmpl).render(ironic_candidates=ironic_candidates)
            ) or []
            needs_bios = env.from_string(bios_tmpl).render(ironic_provisioned_machines=ironic_provisioned)
            needs_uefi = env.from_string(uefi_tmpl).render(ironic_provisioned_machines=ironic_provisioned)
            return len(ironic_provisioned), needs_bios == "True", needs_uefi == "True"

        fixtures = [
            ("all pre-provisioned (deployed servers)", [machine(pre_provisioned=True)], [], 0, False, False),
            ("one ironic bios machine", [machine(pre_provisioned=False, pm_mode="bios")], [], 1, True, False),
            ("one ironic uefi machine", [], [machine(pre_provisioned=False, pm_mode="uefi")], 1, False, True),
            (
                "pm block present but mode unset defaults to bios",
                [machine(pre_provisioned=False, pm_mode="unset")], [],
                1, True, False,
            ),
            (
                "pm block missing entirely does not crash, defaults to bios",
                [machine(pre_provisioned=False, has_pm=False)], [],
                1, True, False,
            ),
            (
                "mixed bios and uefi",
                [machine(pre_provisioned=False, pm_mode="bios")],
                [machine(pre_provisioned=False, pm_mode="uefi")],
                2, True, True,
            ),
        ]

        for label, lm, pm, exp_count, exp_bios, exp_uefi in fixtures:
            count, got_bios, got_uefi = compute(lm, pm)
            if count == exp_count and got_bios == exp_bios and got_uefi == exp_uefi:
                print(f"  OK   director image logic: {label}")
            else:
                ok = False
                print(
                    f"  FAIL director image logic: {label}: expected (count={exp_count}, bios={exp_bios}, "
                    f"uefi={exp_uefi}), got (count={count}, bios={got_bios}, uefi={got_uefi})"
                )

    except StopIteration:
        ok = False
        print(f"  FAIL {UNDERCLOUD_MAIN_FILE}: director image tasks not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {UNDERCLOUD_MAIN_FILE} director image logic check: {e}")

# 10. Checks for the "unquoted rh_password / swallowed registration failures" fix in
#     pre_deployment.sh.j2: the raw subscription-manager shell commands must be gone,
#     replaced with proper modules, with force_register=yes (so reruns against an
#     already-registered node don't fail) and real failure handling (no bare || true).
#     All checks are scoped to the specific fragment that was changed - the file has
#     other, unrelated -m raw / || true usage (MySQL cleanup, ceph prep) that's out of
#     scope and must NOT trip these checks.
PRE_DEPLOYMENT_FILE = "roles/RHOSP-undercloud/templates/pre_deployment.sh.j2"
FRAGMENT_START = "{% if deployed_server[leaf.name] and (rh_activationkey is defined"
FRAGMENT_END = '{{ ansible_adhoc }} -m dnf -a "name=* state=latest"\n{% endif %}'

try:
    with open(PRE_DEPLOYMENT_FILE) as fh:
        pre_deployment = fh.read()
    start_idx = pre_deployment.index(FRAGMENT_START)
    end_idx = pre_deployment.index(FRAGMENT_END) + len(FRAGMENT_END)
    fragment = pre_deployment[start_idx:end_idx]

    if "-m raw" in fragment:
        ok = False
        print(f"  FAIL {PRE_DEPLOYMENT_FILE}: registration section still uses the raw module")
    else:
        print(f"  OK   {PRE_DEPLOYMENT_FILE}: registration section no longer uses the raw module")

    if "-m redhat_subscription" in fragment and "-m rhsm_repository" in fragment:
        print(f"  OK   {PRE_DEPLOYMENT_FILE}: uses redhat_subscription/rhsm_repository modules")
    else:
        ok = False
        print(f"  FAIL {PRE_DEPLOYMENT_FILE}: missing redhat_subscription/rhsm_repository module calls")

    if "force_register=yes" in fragment:
        print(f"  OK   {PRE_DEPLOYMENT_FILE}: registration uses force_register=yes (safe on reruns)")
    else:
        ok = False
        print(f"  FAIL {PRE_DEPLOYMENT_FILE}: registration no longer forces re-registration on reruns")

    if "|| true" in fragment:
        ok = False
        print(f"  FAIL {PRE_DEPLOYMENT_FILE}: registration section still silently swallows failures with '|| true'")
    else:
        print(f"  OK   {PRE_DEPLOYMENT_FILE}: registration section no longer silently swallows failures")

except Exception as e:
    ok = False
    print(f"  FAIL {PRE_DEPLOYMENT_FILE} content check: {e}")

# Render just the changed fragment (not the whole file, which references many
# unrelated variables from other sections) for both registration paths, with and
# without a pool, since the ad-hoc -a argument string is built with nested Jinja
# conditionals.
if jinja2 is None:
    print("  SKIP pre_deployment.sh.j2 render tests: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(PRE_DEPLOYMENT_FILE) as fh:
            pre_deployment_src = fh.read()

        start_idx = pre_deployment_src.index(FRAGMENT_START)
        end_idx = pre_deployment_src.index(FRAGMENT_END) + len(FRAGMENT_END)
        fragment = pre_deployment_src[start_idx:end_idx]

        base_context = {
            "leaf": {"name": "overcloud"},
            "deployed_server": {"overcloud": True},
            "RHOSP_version_supported": {
                17.1: {
                    "overcloud_ssh_user": "tripleo-admin",
                    "rhel_release": "9.2",
                    "nodes_repos": ["repo-a", "repo-b"],
                }
            },
            "RHOSP_version": 17.1,
        }

        render_fixtures = [
            ("activation key, no pool", {"rh_orgid": "myorg", "rh_activationkey": "mykey"}),
            ("activation key, with pool", {"rh_orgid": "myorg", "rh_activationkey": "mykey", "rh_pool": "mypool"}),
            ("username/password, no pool", {"rh_username": "admin", "rh_password": "S3cr3t!"}),
            (
                "username/password, with pool",
                {"rh_username": "admin", "rh_password": "p@ss w0rd", "rh_pool": "mypool"},
            ),
        ]

        env = make_env()
        for label, creds in render_fixtures:
            try:
                rendered = env.from_string(fragment).render(**base_context, **creds)
                if "-m redhat_subscription" in rendered and "-m rhsm_repository" in rendered:
                    print(f"  OK   {PRE_DEPLOYMENT_FILE}: renders cleanly for {label}")
                else:
                    ok = False
                    print(f"  FAIL {PRE_DEPLOYMENT_FILE}: rendered output missing expected module calls for {label}")
            except Exception as e:
                ok = False
                print(f"  FAIL {PRE_DEPLOYMENT_FILE}: failed to render for {label}: {e}")

    except Exception as e:
        ok = False
        print(f"  FAIL {PRE_DEPLOYMENT_FILE} render check setup: {e}")

# 11. Checks for the "plaintext RH credentials written world-readable" fix: the
#     credential-bearing files must now be rendered in their own task with a
#     restrictive mode, split out of the shared loop that still renders their
#     unrelated, non-secret sibling templates.
CRED_TASK_CHECKS = [
    (
        "roles/RHOSP-undercloud/tasks/main.yml",
        "CONFIGFILES - Set container images prepare file (contains registry credentials)",
        "/home/stack/containers-prepare-parameter.yaml",
        "0600",
    ),
    (
        "roles/RHOSP-undercloud/tasks/overcloud.yml",
        "TEMPLATES - Prepare the overcloud environment file (contains RHSM credentials when RegisterNodes is set)",
        "/home/stack/templates/custom-overcloud.yaml",
        "0600",
    ),
    (
        "roles/RHOSP-undercloud/tasks/overcloud.yml",
        "SCRIPTS - Prepare the pre-deployment script (contains RHSM credentials)",
        "/home/stack/pre_deployment.sh",
        "0700",
    ),
    (
        "roles/RHOSP-undercloud/tasks/leafs.yml",
        "TEMPLATES - Prepare the overcloud environment file for {{ leaf.name }} (contains RHSM credentials when RegisterNodes is set)",
        "/home/stack/templates/{{ leaf.name }}/custom-overcloud.yaml",
        "0600",
    ),
    (
        "roles/RHOSP-undercloud/tasks/leafs.yml",
        "SCRIPTS - Prepare the pre-deployment script for {{ leaf.name }} (contains RHSM credentials)",
        "/home/stack/templates/{{ leaf.name }}/pre_deployment.sh",
        "0700",
    ),
]

for file_path, task_name, expected_dest, expected_mode in CRED_TASK_CHECKS:
    try:
        with open(file_path) as fh:
            tasks = yaml.safe_load(fh)
        task = next(t for t in tasks if t.get("name") == task_name)
        actual_dest = task["template"]["dest"]
        actual_mode = str(task["template"].get("mode", "")).strip("\"'")
        if actual_dest == expected_dest and actual_mode == expected_mode:
            print(f"  OK   {file_path}: '{task_name}' -> {expected_dest} mode {expected_mode}")
        else:
            ok = False
            print(
                f"  FAIL {file_path}: '{task_name}' has dest={actual_dest!r} mode={actual_mode!r}, "
                f"expected dest={expected_dest!r} mode={expected_mode!r}"
            )
    except StopIteration:
        ok = False
        print(f"  FAIL {file_path}: task '{task_name}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {file_path} credential-file-mode check: {e}")

# Confirm the now-split-out files were actually removed from their old shared loops
# (otherwise they'd be rendered twice, once restricted and once with the loop's
# looser/no mode).
SHARED_LOOP_CHECKS = [
    ("roles/RHOSP-undercloud/tasks/main.yml", "CONFIGFILES - Set custom undercloud parameters", None),
    ("roles/RHOSP-undercloud/tasks/overcloud.yml", "TEMPLATES - Prepare templates", "custom-overcloud.yaml"),
    ("roles/RHOSP-undercloud/tasks/overcloud.yml", "SCRIPTS - Prepare the scripts", "pre_deployment.sh"),
    ("roles/RHOSP-undercloud/tasks/leafs.yml", "TEMPLATES - Prepare templates for {{ leaf.name }}", "custom-overcloud.yaml"),
    ("roles/RHOSP-undercloud/tasks/leafs.yml", "SCRIPTS - Prepare the scripts", "pre_deployment.sh"),
]

for file_path, task_name, excluded_item in SHARED_LOOP_CHECKS:
    try:
        with open(file_path) as fh:
            tasks = yaml.safe_load(fh)
        task = next(t for t in tasks if t.get("name") == task_name)
        loop_items = task.get("loop", [])
        if excluded_item is None or excluded_item not in loop_items:
            print(f"  OK   {file_path}: '{task_name}' no longer includes the credential-bearing file in its loop")
        else:
            ok = False
            print(f"  FAIL {file_path}: '{task_name}' still renders {excluded_item!r} via the shared (unrestricted) loop")
    except StopIteration:
        ok = False
        print(f"  FAIL {file_path}: task '{task_name}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {file_path} shared-loop check: {e}")

# 12. Check for the "STORAGE - Deactivate the pool missing existence guard" fix:
#     both the deactivate and delete tasks must now check ansible_libvirt_pools[item]
#     is defined before acting on a possibly-nonexistent pool.
STORAGE_FILE = "roles/RHOSP-virt-infra/tasks/clean_libvirt_storage.yml"
GUARD = "ansible_libvirt_pools[item] is defined"

try:
    with open(STORAGE_FILE) as fh:
        storage_tasks = yaml.safe_load(fh)
    deactivate_task = next(t for t in storage_tasks if t.get("name") == "STORAGE - Deactivate the pool")
    delete_task = next(t for t in storage_tasks if t.get("name") == "STORAGE - Delete the pool")

    if deactivate_task.get("when") == GUARD:
        print(f"  OK   {STORAGE_FILE}: 'Deactivate the pool' now guards on pool existence")
    else:
        ok = False
        print(f"  FAIL {STORAGE_FILE}: 'Deactivate the pool' missing the existence guard: {deactivate_task.get('when')!r}")

    if delete_task.get("when") == GUARD:
        print(f"  OK   {STORAGE_FILE}: 'Delete the pool' still guards on pool existence")
    else:
        ok = False
        print(f"  FAIL {STORAGE_FILE}: 'Delete the pool' lost its existence guard: {delete_task.get('when')!r}")

except StopIteration:
    ok = False
    print(f"  FAIL {STORAGE_FILE}: expected tasks not found")
except Exception as e:
    ok = False
    print(f"  FAIL {STORAGE_FILE} guard check: {e}")

# 13. Logic check for the "misleading oc apply/delete instructions" fix: render the
#     real deployment/cleanup instruction messages for kubevirt_undercloud True/False
#     and confirm the 04-routes.yaml/06-undercloud.yaml lines only appear when true.
DEPLOY_INSTRUCTIONS_TASK = "KUBERNETES - Display deployment instructions"
CLEANUP_INSTRUCTIONS_TASK = "KUBERNETES - Display cleanup instructions"

if jinja2 is None:
    print("  SKIP oc apply/delete instructions logic tests: jinja2 not installed (pip install jinja2)")
else:
    env = make_env()
    instr_context = {"playbook_dir": "/home/admin/RHOSPVirtLab", "KubeVirtNamespace": "rhosp-lab", "datavolume_name": "rhel-image"}

    try:
        with open("roles/RHOSP-kubevirt-infra/tasks/create_kubernetes_resources.yml") as fh:
            create_tasks = yaml.safe_load(fh)
        deploy_task = next(t for t in create_tasks if t.get("name") == DEPLOY_INSTRUCTIONS_TASK)
        deploy_tmpl = deploy_task["vars"]["deployment_instructions"]

        for kubevirt_undercloud, label in [(True, "kubevirt undercloud"), (False, "non-kubevirt undercloud")]:
            rendered = env.from_string(deploy_tmpl).render(kubevirt_undercloud=kubevirt_undercloud, **instr_context)
            has_routes = "04-routes.yaml" in rendered
            has_undercloud_vm = "06-undercloud.yaml" in rendered
            if has_routes == kubevirt_undercloud and has_undercloud_vm == kubevirt_undercloud:
                print(f"  OK   deployment instructions ({label}): 04-routes/06-undercloud shown only when expected")
            else:
                ok = False
                print(
                    f"  FAIL deployment instructions ({label}): 04-routes present={has_routes}, "
                    f"06-undercloud present={has_undercloud_vm}, expected both={kubevirt_undercloud}"
                )

    except StopIteration:
        ok = False
        print(f"  FAIL create_kubernetes_resources.yml: task '{DEPLOY_INSTRUCTIONS_TASK}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL deployment instructions logic check: {e}")

    try:
        with open(KUBEVIRT_MAIN_FILE) as fh:
            kubevirt_tasks = yaml.safe_load(fh)
        cleanup_task = next(t for t in kubevirt_tasks if t.get("name") == CLEANUP_INSTRUCTIONS_TASK)
        cleanup_tmpl = cleanup_task["debug"]["msg"]

        for kubevirt_undercloud, label in [(True, "kubevirt undercloud"), (False, "non-kubevirt undercloud")]:
            rendered = env.from_string(cleanup_tmpl).render(kubevirt_undercloud=kubevirt_undercloud, **instr_context)
            has_routes = "04-routes.yaml" in rendered
            has_undercloud_vm = "06-undercloud.yaml" in rendered
            if has_routes == kubevirt_undercloud and has_undercloud_vm == kubevirt_undercloud:
                print(f"  OK   cleanup instructions ({label}): 04-routes/06-undercloud shown only when expected")
            else:
                ok = False
                print(
                    f"  FAIL cleanup instructions ({label}): 04-routes present={has_routes}, "
                    f"06-undercloud present={has_undercloud_vm}, expected both={kubevirt_undercloud}"
                )

    except StopIteration:
        ok = False
        print(f"  FAIL {KUBEVIRT_MAIN_FILE}: task '{CLEANUP_INSTRUCTIONS_TASK}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL cleanup instructions logic check: {e}")

# 14. Check for the "credentials printed in Ansible output" fix: the tasks that embed
#     real secrets (BMC password, RH subscription password/activationkey) in
#     command/raw/redhat_subscription must now set no_log: true.
NO_LOG_TASK_CHECKS = [
    ("roles/RHOSP-virt-infra/tasks/create_virtualbmc.yml", "VIRTUALBMC - Ensure node exists"),
    ("roles/RHOSP-undercloud/tasks/subscription.yml", "SUBSCRIPTION - Register the undercloud (with OrgID and Activation Key)"),
    ("roles/RHOSP-undercloud/tasks/subscription.yml", "SUBSCRIPTION - Register the undercloud with raw (with OrgID and Activation Key, fallback)"),
    ("roles/RHOSP-undercloud/tasks/subscription.yml", "SUBSCRIPTION - Register the undercloud (with username and password)"),
    ("roles/RHOSP-undercloud/tasks/subscription.yml", "SUBSCRIPTION - Register the undercloud with raw (with username and password, fallback)"),
]

for file_path, task_name in NO_LOG_TASK_CHECKS:
    try:
        with open(file_path) as fh:
            tasks = yaml.safe_load(fh)
        task = next(t for t in tasks if t.get("name") == task_name)
        if task.get("no_log") is True:
            print(f"  OK   {file_path}: '{task_name}' sets no_log: true")
        else:
            ok = False
            print(f"  FAIL {file_path}: '{task_name}' missing no_log: true")
    except StopIteration:
        ok = False
        print(f"  FAIL {file_path}: task '{task_name}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {file_path} no_log check: {e}")

# 15. Logic check for the "network-config.j2 unguarded None dereference" fix: render
#     the real `matching_leaf_names` Jinja template (pulled from the new CHECKS task)
#     against synthetic leafs/machine fixtures, mirroring the template's own
#     `machine.libvirt.hypervisor in l.hypervisor.split(',')` matching logic.
CLOUD_INIT_FILE = "roles/RHOSP-virt-infra/tasks/create_libvirt_cloud_init.yml"
LEAF_CHECK_TASK_NAME = "CHECKS - Ensure {{ machine.name }} resolves to a known leaf before rendering its network-config"

if jinja2 is None:
    print("  SKIP matching_leaf_names logic tests: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(CLOUD_INIT_FILE) as fh:
            cloud_init_tasks = yaml.safe_load(fh)
        leaf_check_task = next(t for t in cloud_init_tasks if t.get("name") == LEAF_CHECK_TASK_NAME)
        template_src = leaf_check_task["vars"]["matching_leaf_names"]

        env = make_env()

        def matching_leaves(hypervisor, leafs):
            rendered = env.from_string(template_src).render(
                machine={"libvirt": {"hypervisor": hypervisor}}, leafs=leafs
            )
            return yaml.safe_load(rendered) or []

        fixtures = [
            ("exact single-hypervisor match", "hyperv2", [{"name": "overcloud", "hypervisor": "hyperv2"}], ["overcloud"]),
            ("no match (typo)", "hyperv2", [{"name": "overcloud", "hypervisor": "hypervisor2"}], []),
            (
                "match within a multi-hypervisor leaf",
                "hyperv2",
                [{"name": "overcloud", "hypervisor": "localhost,hyperv2"}],
                ["overcloud"],
            ),
            ("no leafs at all", "hyperv2", [], []),
        ]

        for label, hypervisor, leafs, expected in fixtures:
            result = matching_leaves(hypervisor, leafs)
            if result == expected:
                print(f"  OK   matching_leaf_names logic: {label}")
            else:
                ok = False
                print(f"  FAIL matching_leaf_names logic: {label}: expected {expected}, got {result}")

    except StopIteration:
        ok = False
        print(f"  FAIL {CLOUD_INIT_FILE}: task '{LEAF_CHECK_TASK_NAME}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {CLOUD_INIT_FILE} matching_leaf_names check: {e}")

# 16. Content check for the "stale VirtualBMC/KubeVirtBMC TODO" fix: the comment must
#     no longer imply VirtualBMC was ever implemented for kubevirt (nothing to
#     "replace"), and should instead describe adding pm support once KubeVirtBMC exists.
try:
    with open(KUBEVIRT_MAIN_FILE) as fh:
        kubevirt_main_src = fh.read()

    if "Replace VirtualBMC with KubeVirtBMC" in kubevirt_main_src:
        ok = False
        print(f"  FAIL {KUBEVIRT_MAIN_FILE}: TODO still implies VirtualBMC needs replacing")
    else:
        print(f"  OK   {KUBEVIRT_MAIN_FILE}: TODO no longer implies VirtualBMC needs replacing")

    if "Add power management (pm) support for kubevirt machines via KubeVirtBMC" in kubevirt_main_src:
        print(f"  OK   {KUBEVIRT_MAIN_FILE}: TODO now describes adding pm support via KubeVirtBMC")
    else:
        ok = False
        print(f"  FAIL {KUBEVIRT_MAIN_FILE}: TODO no longer describes adding pm support via KubeVirtBMC")

except Exception as e:
    ok = False
    print(f"  FAIL {KUBEVIRT_MAIN_FILE} TODO content check: {e}")

# 17. Check for the "community.general.nmcli -> raw nmcli" REVERT in
#     clean_network_profiles.yml: community.general.nmcli's module ships code using
#     `from __future__ import annotations` (Python 3.7+), which SyntaxErrors on a
#     Python 3.6 target (e.g. RHEL 8) - confirmed by a real deployment failure - so
#     both delete tasks must be back to command-based nmcli with rc 10 (not found)
#     treated as an idempotent no-op, not a real failure.
NMCLI_FILE = "roles/RHOSP-virt-infra/tasks/clean_network_profiles.yml"
NMCLI_TASK_NAMES = [
    "NETWORKING - Delete VLAN connections via nmcli",
    "NETWORKING - Delete bridge connections via nmcli",
]

try:
    with open(NMCLI_FILE) as fh:
        nmcli_src = fh.read()
        nmcli_tasks = yaml.safe_load(nmcli_src)

    if re.search(r"community\.general\.nmcli:", nmcli_src):
        ok = False
        print(f"  FAIL {NMCLI_FILE}: community.general.nmcli is still present (Python 3.6 incompatible)")
    else:
        print(f"  OK   {NMCLI_FILE}: community.general.nmcli fully removed")

    for task_name in NMCLI_TASK_NAMES:
        task = next(t for t in nmcli_tasks if t.get("name") == task_name)
        if (
            task.get("command", "").startswith("nmcli connection delete")
            and task.get("failed_when", "").endswith("not in [0, 10]")
            and task.get("changed_when", "").endswith("== 0")
        ):
            print(f"  OK   {NMCLI_FILE}: '{task_name}' uses command-based nmcli with rc 10 as no-op")
        else:
            ok = False
            print(f"  FAIL {NMCLI_FILE}: '{task_name}' not properly reverted: {task}")
except StopIteration:
    ok = False
    print(f"  FAIL {NMCLI_FILE}: expected nmcli tasks not found")
except Exception as e:
    ok = False
    print(f"  FAIL {NMCLI_FILE} nmcli check: {e}")

# 18. Check for the firewalld zone-creation task: REVERTED from an earlier attempt
#     that set immediate: yes on the zone itself - the firewalld module rejects
#     immediate: yes for zone-level operations ("Zone operations must be permanent"),
#     confirmed by a real failure on a live run. Zone creation must stay
#     permanent-only, paired with an explicit conditional reload to activate it now.
FIREWALL_FILE = "roles/RHOSP-virt-infra/tasks/configure_firewall.yml"
ZONE_TASK_NAME = "FIREWALLD - Ensure libvirt zone exists"
RELOAD_TASK_NAME = "FIREWALLD - Reload firewall after creating the zone"

try:
    with open(FIREWALL_FILE) as fh:
        firewall_tasks = yaml.safe_load(fh)

    zone_task = next(t for t in firewall_tasks if t.get("name") == ZONE_TASK_NAME)
    if zone_task.get("firewalld", {}).get("immediate") is not True:
        print(f"  OK   {FIREWALL_FILE}: '{ZONE_TASK_NAME}' does not set immediate: yes (would fail - zone ops must be permanent-only)")
    else:
        ok = False
        print(f"  FAIL {FIREWALL_FILE}: '{ZONE_TASK_NAME}' sets immediate: yes, which firewalld rejects for zone operations")

    reload_task = next(t for t in firewall_tasks if t.get("name") == RELOAD_TASK_NAME)
    if reload_task.get("command") == "firewall-cmd --reload" and reload_task.get("when") == "firewalld_create_zone.changed":
        print(f"  OK   {FIREWALL_FILE}: '{RELOAD_TASK_NAME}' present and gated on the zone task's changed result")
    else:
        ok = False
        print(f"  FAIL {FIREWALL_FILE}: '{RELOAD_TASK_NAME}' missing or malformed: {reload_task}")

except StopIteration:
    ok = False
    print(f"  FAIL {FIREWALL_FILE}: expected tasks not found")
except Exception as e:
    ok = False
    print(f"  FAIL {FIREWALL_FILE} check: {e}")

# 19. Check for the "shell block for oc/kubectl extraction" -> proper modules fix in
#     RHOSP-kubevirt-infra/tasks/setup.yml: must now use unarchive/file instead of a
#     shell script, and the shell task must be gone entirely.
KUBEVIRT_SETUP_FILE = "roles/RHOSP-kubevirt-infra/tasks/setup.yml"

try:
    with open(KUBEVIRT_SETUP_FILE) as fh:
        setup_tasks = yaml.safe_load(fh)

    extract_task = next(t for t in setup_tasks if t.get("name") == "SETUP - Extract openshift-client to ~/bin")
    unarchive_params = extract_task.get("unarchive")
    if unarchive_params and sorted(unarchive_params.get("include", [])) == ["kubectl", "oc"] and unarchive_params.get("remote_src"):
        print(f"  OK   {KUBEVIRT_SETUP_FILE}: extraction uses unarchive with include=[oc, kubectl]")
    else:
        ok = False
        print(f"  FAIL {KUBEVIRT_SETUP_FILE}: extraction task does not properly use unarchive: {extract_task}")
    if "shell" in extract_task:
        ok = False
        print(f"  FAIL {KUBEVIRT_SETUP_FILE}: extraction task still has a leftover shell key")

    perms_task = next(t for t in setup_tasks if t.get("name") == "SETUP - Ensure oc/kubectl have the right permissions")
    if perms_task.get("file", {}).get("mode") == "0755" and sorted(perms_task.get("loop", [])) == ["kubectl", "oc"]:
        print(f"  OK   {KUBEVIRT_SETUP_FILE}: permissions task sets mode 0755 for oc/kubectl via file module")
    else:
        ok = False
        print(f"  FAIL {KUBEVIRT_SETUP_FILE}: permissions task missing or malformed: {perms_task}")

    cleanup_task = next(t for t in setup_tasks if t.get("name") == "SETUP - Remove the downloaded openshift-client archive")
    if cleanup_task.get("file", {}).get("state") == "absent":
        print(f"  OK   {KUBEVIRT_SETUP_FILE}: archive cleanup uses file state=absent")
    else:
        ok = False
        print(f"  FAIL {KUBEVIRT_SETUP_FILE}: archive cleanup task missing or malformed: {cleanup_task}")

except StopIteration:
    ok = False
    print(f"  FAIL {KUBEVIRT_SETUP_FILE}: expected tasks not found")
except Exception as e:
    ok = False
    print(f"  FAIL {KUBEVIRT_SETUP_FILE} check: {e}")

# 20. Checks for the "generated bash script + MAC-grep + nmcli raw commands" fix in
#     undercloud-network.yml: the script-generation/execution must be gone, replaced
#     with fact-based MAC resolution; connection creation uses raw nmcli (NOT
#     community.general.nmcli, which was tried and reverted after a real deployment
#     SyntaxError on a Python 3.6 target); and the real resolved_ifname Jinja
#     template is rendered against synthetic ansible_facts.
UNDERCLOUD_NET_FILE = "roles/RHOSP-undercloud/tasks/undercloud-network.yml"
RESOLVE_TASK_NAME = "UNDERCLOUD NETWORK - Resolve each gateway interface's MAC address to its kernel name and connection name"

try:
    with open(UNDERCLOUD_NET_FILE) as fh:
        undercloud_net_src = fh.read()

    if "configure_gw_networks.sh" in undercloud_net_src:
        ok = False
        print(f"  FAIL {UNDERCLOUD_NET_FILE}: generated script approach is still present")
    else:
        print(f"  OK   {UNDERCLOUD_NET_FILE}: generated script approach is gone")

    if re.search(r"community\.general\.nmcli:", undercloud_net_src):
        ok = False
        print(f"  FAIL {UNDERCLOUD_NET_FILE}: community.general.nmcli is still present (Python 3.6 incompatible)")
    else:
        print(f"  OK   {UNDERCLOUD_NET_FILE}: community.general.nmcli fully removed")

    if "nmcli connection add type ethernet" in undercloud_net_src and "nmcli connection modify" in undercloud_net_src:
        print(f"  OK   {UNDERCLOUD_NET_FILE}: uses command-based nmcli add/modify for connection creation")
    else:
        ok = False
        print(f"  FAIL {UNDERCLOUD_NET_FILE}: missing command-based nmcli add/modify logic")

    if "ip link show" in undercloud_net_src:
        ok = False
        print(f"  FAIL {UNDERCLOUD_NET_FILE}: still shells out to 'ip link show' for MAC resolution")
    else:
        print(f"  OK   {UNDERCLOUD_NET_FILE}: no more shelling out to 'ip link show'")

except Exception as e:
    ok = False
    print(f"  FAIL {UNDERCLOUD_NET_FILE} content check: {e}")

if jinja2 is None:
    print("  SKIP resolved_ifname logic tests: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(UNDERCLOUD_NET_FILE) as fh:
            undercloud_net_tasks = yaml.safe_load(fh)
        block_task = undercloud_net_tasks[0]
        resolve_task = next(t for t in block_task["block"] if t.get("name") == RESOLVE_TASK_NAME)
        template_src = resolve_task["vars"]["resolved_ifname"]

        fake_hostvars = {
            "undercloud": {
                "ansible_facts": {
                    "interfaces": ["lo", "eth0", "eth1"],
                    "lo": {},
                    "eth0": {"macaddress": "52:54:00:11:22:33"},
                    "eth1": {"macaddress": "52:54:00:44:55:66"},
                }
            }
        }

        env = make_env()

        def resolve(mac):
            return env.from_string(template_src).render(item={"mac": mac}, hostvars=fake_hostvars).strip()

        fixtures = [
            ("exact match, lowercase", "52:54:00:11:22:33", "eth0"),
            ("exact match, uppercase MAC in input", "52:54:00:44:55:66".upper(), "eth1"),
            ("no match", "52:54:00:99:99:99", "None"),
        ]

        for label, mac, expected in fixtures:
            result = resolve(mac)
            if result == expected:
                print(f"  OK   resolved_ifname logic: {label}")
            else:
                ok = False
                print(f"  FAIL resolved_ifname logic: {label}: expected {expected!r}, got {result!r}")

    except StopIteration:
        ok = False
        print(f"  FAIL {UNDERCLOUD_NET_FILE}: task '{RESOLVE_TASK_NAME}' not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {UNDERCLOUD_NET_FILE} resolved_ifname logic check: {e}")

    try:
        with open(UNDERCLOUD_NET_FILE) as fh:
            undercloud_net_tasks2 = yaml.safe_load(fh)
        block_task2 = undercloud_net_tasks2[0]
        create_task = next(
            t for t in block_task2["block"]
            if t.get("name") == "UNDERCLOUD NETWORK - Create or update gateway network connections via NetworkManager"
        )
        cmd_template = create_task["command"]
        changed_when_expr = create_task["changed_when"]

        env = make_env()
        fake_item = {"conn_name": "external", "ifname": "eth2", "bridge": "br-external"}
        fake_bridge_to_gw = {"br-external": {"subnet": {"gateway": "10.1.0.254", "ip_subnet": "10.1.0.0/24"}}}

        for label, existing, expect_verb in [
            ("new connection (first run)", [], "add type ethernet con-name external"),
            ("existing connection (subsequent run)", ["external"], "modify external"),
        ]:
            rendered_cmd = env.from_string(cmd_template).render(
                item=fake_item,
                gw_existing_connections={"stdout_lines": existing},
                bridge_to_gw=fake_bridge_to_gw,
            )
            if expect_verb in rendered_cmd and "10.1.0.254/24" in rendered_cmd:
                print(f"  OK   create-or-update nmcli command logic: {label}")
            else:
                ok = False
                print(f"  FAIL create-or-update nmcli command logic: {label}: {rendered_cmd!r}")

            compiled_changed = env.compile_expression(changed_when_expr)
            expected_changed = existing == []
            got_changed = bool(compiled_changed(item=fake_item, gw_existing_connections={"stdout_lines": existing}))
            if got_changed == expected_changed:
                print(f"  OK   create-or-update changed_when logic: {label}")
            else:
                ok = False
                print(f"  FAIL create-or-update changed_when logic: {label}: expected {expected_changed}, got {got_changed}")

    except StopIteration:
        ok = False
        print(f"  FAIL {UNDERCLOUD_NET_FILE}: 'Create or update gateway network connections' task not found")
    except Exception as e:
        ok = False
        print(f"  FAIL {UNDERCLOUD_NET_FILE} create-or-update logic check: {e}")

# 21. Logic check for the "pre_deployment.sh references overcloud-full.qcow2
#     unconditionally" fix: render the real image-upload fragment for both
#     needs_bios_image=True and False on RHOSP >= 17.1, and confirm the explicit
#     overcloud-full.qcow2 re-upload only appears when the BIOS image is needed.
IMAGE_FRAGMENT_START = "# Prepare the overcloud"
IMAGE_FRAGMENT_END = "ls -al /var/lib/ironic/images/\n{% else %}\nopenstack image list --fit-width\n{% endif %}"

if jinja2 is None:
    print("  SKIP pre_deployment.sh.j2 image-upload logic tests: jinja2 not installed (pip install jinja2)")
else:
    try:
        with open(PRE_DEPLOYMENT_FILE) as fh:
            pre_deployment_src = fh.read()
        start_idx = pre_deployment_src.index(IMAGE_FRAGMENT_START)
        end_idx = pre_deployment_src.index(IMAGE_FRAGMENT_END) + len(IMAGE_FRAGMENT_END)
        image_fragment = pre_deployment_src[start_idx:end_idx]

        env = make_env()
        for needs_bios, label in [(True, "needs_bios_image=True"), (False, "needs_bios_image=False")]:
            rendered = env.from_string(image_fragment).render(RHOSP_version=17.1, needs_bios_image=needs_bios)
            has_bios_upload = "--os-image-name overcloud-full.qcow2" in rendered
            if has_bios_upload == needs_bios:
                print(f"  OK   pre_deployment.sh.j2 image upload ({label}): overcloud-full.qcow2 upload matches expectation")
            else:
                ok = False
                print(f"  FAIL pre_deployment.sh.j2 image upload ({label}): expected upload present={needs_bios}, got {has_bios_upload}")

        # 16.2 path must be untouched by this fix (no bios-specific gating there).
        rendered_162 = env.from_string(image_fragment).render(RHOSP_version=16.2, needs_bios_image=False)
        if "openstack image list --fit-width" in rendered_162:
            print("  OK   pre_deployment.sh.j2 image upload (16.2): unaffected by the needs_bios_image fix")
        else:
            ok = False
            print(f"  FAIL pre_deployment.sh.j2 image upload (16.2): unexpected render: {rendered_162!r}")

    except Exception as e:
        ok = False
        print(f"  FAIL pre_deployment.sh.j2 image upload logic check: {e}")

# 22. Checks for the manual "NetworkParameterDefaults/OvercloudParameterDefaults"
#     refactor review: the critical indent(first=True) fix must be in place (without
#     it, the first injected key escapes the parameter_defaults mapping and becomes
#     an invalid top-level sibling key - confirmed by actually rendering+parsing the
#     real template tail, not just a string search), the old Compute*Properties /
#     BridgeMappings / NetworkVlanRanges variables must be fully gone, and the docs
#     must reference the new variables instead of the old ones.
NETWORK_CONFIG_FILE = "roles/RHOSP-undercloud/templates/custom-network-configuration.yaml.j2"
OVERCLOUD_TEMPLATE_FILE = "roles/RHOSP-undercloud/templates/custom-overcloud.yaml.j2"
OLD_NFV_NAMES = [
    "ComputeSriovProperties", "ComputeOvsHwOffloadProperties",
    "ComputeOvsDpdkProperties", "ComputeOvsDpdkSriovProperties",
    "BridgeMappings", "NetworkVlanRanges",
]


def find_old_name_hits(src, names):
    # "BridgeMappings" is a substring of the still-valid "RoleBridgeMappings" and
    # the new "NeutronBridgeMappings" - only flag the old bare top-level name.
    hits = []
    for name in names:
        if name == "BridgeMappings":
            if re.search(r"(?<!Role)(?<!Neutron)BridgeMappings", src):
                hits.append(name)
        elif name in src:
            hits.append(name)
    return hits


for file_path in ["vars/options.yml", "roles/RHOSP-undercloud/defaults/main.yml"]:
    try:
        with open(file_path) as fh:
            src = fh.read()
        leftovers = find_old_name_hits(src, OLD_NFV_NAMES)
        if leftovers:
            ok = False
            print(f"  FAIL {file_path}: old NFV/network variable(s) still present: {leftovers}")
        else:
            print(f"  OK   {file_path}: old NFV/network variables fully removed")
    except Exception as e:
        ok = False
        print(f"  FAIL {file_path} old-variable check: {e}")

if jinja2 is None:
    print("  SKIP NetworkParameterDefaults/OvercloudParameterDefaults indent logic tests: jinja2 not installed")
else:
    for file_path, var_name in [
        (NETWORK_CONFIG_FILE, "NetworkParameterDefaults"),
        (OVERCLOUD_TEMPLATE_FILE, "OvercloudParameterDefaults"),
    ]:
        try:
            with open(file_path) as fh:
                lines = fh.readlines()
            last_line = lines[-1].rstrip("\n")

            if "to_nice_yaml" not in last_line:
                ok = False
                print(f"  FAIL {file_path}: last line does not use to_nice_yaml (block-style lists): {last_line!r}")
                continue

            if "indent(width=2, first=True)" not in last_line:
                ok = False
                print(f"  FAIL {file_path}: last line does not use indent(width=2, first=True): {last_line!r}")
                continue

            fragment = "parameter_defaults:\n  ExistingKey: existing_value\n\n" + last_line
            env = make_env()
            rendered = env.from_string(fragment).render(**{var_name: {
                "InjectedKeyOne": "value_one",
                "InjectedKeyTwo": "value_two",
                "InjectedListKey": ["ItemOne", "ItemTwo", "ItemThree"],
            }})
            parsed = yaml.safe_load(rendered)

            if (
                isinstance(parsed, dict)
                and list(parsed.keys()) == ["parameter_defaults"]
                and parsed["parameter_defaults"].get("ExistingKey") == "existing_value"
                and parsed["parameter_defaults"].get("InjectedKeyOne") == "value_one"
                and parsed["parameter_defaults"].get("InjectedKeyTwo") == "value_two"
                and parsed["parameter_defaults"].get("InjectedListKey") == ["ItemOne", "ItemTwo", "ItemThree"]
            ):
                print(f"  OK   {file_path}: {var_name} renders fully nested under parameter_defaults")
            else:
                ok = False
                print(f"  FAIL {file_path}: {var_name} did not render properly nested: {parsed!r}")

            if "- ItemOne" in rendered and "[ItemOne, ItemTwo" not in rendered:
                print(f"  OK   {file_path}: {var_name} renders lists in block style, not flow style")
            else:
                ok = False
                print(f"  FAIL {file_path}: {var_name} did not render lists in block style: {rendered!r}")

        except Exception as e:
            ok = False
            print(f"  FAIL {file_path} indent logic check: {e}")

# Docs must no longer reference the old variables. The detailed role README should
# document both new dicts; the root README is a high-level summary and only needs
# to be free of the old names (it already points at NetworkParameterDefaults).
DOC_CHECKS = [
    ("README.md", ["NetworkParameterDefaults"]),
    ("roles/RHOSP-undercloud/README.md", ["NetworkParameterDefaults", "OvercloudParameterDefaults"]),
]
for doc_path, required_new_names in DOC_CHECKS:
    try:
        with open(doc_path) as fh:
            doc_src = fh.read()
        leftovers = find_old_name_hits(doc_src, OLD_NFV_NAMES)
        if leftovers:
            ok = False
            print(f"  FAIL {doc_path}: still documents old variable(s): {leftovers}")
        else:
            print(f"  OK   {doc_path}: no longer documents old variables")
        missing_new = [name for name in required_new_names if name not in doc_src]
        if not missing_new:
            print(f"  OK   {doc_path}: documents {', '.join(required_new_names)}")
        else:
            ok = False
            print(f"  FAIL {doc_path}: missing documentation for {missing_new}")
    except Exception as e:
        ok = False
        print(f"  FAIL {doc_path} doc check: {e}")

# 23. Checks for the "nmcli connection up always reports changed" idempotency fix
#     in undercloud-network.yml: a state-query task must now gate the activation
#     task so it's skipped (not run-and-marked-changed) for already-active
#     connections. Render the real `when` condition against synthetic fixtures.
UNDERCLOUD_NETWORK_FILE = "roles/RHOSP-undercloud/tasks/undercloud-network.yml"
QUERY_TASK_NAME = "UNDERCLOUD NETWORK - Get active NetworkManager connections"
ACTIVATE_TASK_NAME = "UNDERCLOUD NETWORK - Activate gateway network connections"

try:
    with open(UNDERCLOUD_NETWORK_FILE) as fh:
        undercloud_network_tasks = yaml.safe_load(fh)
    block_tasks = undercloud_network_tasks[0]["block"]

    query_task = next(t for t in block_tasks if t.get("name") == QUERY_TASK_NAME)
    if query_task.get("changed_when") is False:
        print(f"  OK   {UNDERCLOUD_NETWORK_FILE}: '{QUERY_TASK_NAME}' is a read-only check (changed_when: false)")
    else:
        ok = False
        print(f"  FAIL {UNDERCLOUD_NETWORK_FILE}: '{QUERY_TASK_NAME}' missing changed_when: false")

    activate_task = next(t for t in block_tasks if t.get("name") == ACTIVATE_TASK_NAME)
    old_heuristic_gone = "changed_when" not in activate_task
    when_list = activate_task.get("when", [])
    has_state_guard = any("gw_active_connections" in str(w) for w in when_list)

    if old_heuristic_gone and has_state_guard:
        print(f"  OK   {UNDERCLOUD_NETWORK_FILE}: '{ACTIVATE_TASK_NAME}' gates on real active-connection state, no stdout-parsing heuristic")
    else:
        ok = False
        print(f"  FAIL {UNDERCLOUD_NETWORK_FILE}: '{ACTIVATE_TASK_NAME}' still has the old heuristic or lost the state guard: {activate_task}")

    if jinja2 is None:
        print("  SKIP active-connection guard logic test: jinja2 not installed")
    else:
        guard_expr = next(w for w in when_list if "gw_active_connections" in str(w))
        env = make_env()
        compiled = env.compile_expression(guard_expr)

        fixtures = [
            ("connection already active", "external", ["external", "eth0"], False),
            ("connection not active", "external", ["eth0"], True),
            ("no active connections at all", "external", [], True),
        ]
        for label, conn_name, active_list, expected in fixtures:
            result = bool(compiled(item={"conn_name": conn_name}, gw_active_connections={"stdout_lines": active_list}))
            if result == expected:
                print(f"  OK   activate-gateway guard logic: {label}")
            else:
                ok = False
                print(f"  FAIL activate-gateway guard logic: {label}: expected {expected}, got {result}")

except StopIteration:
    ok = False
    print(f"  FAIL {UNDERCLOUD_NETWORK_FILE}: expected tasks not found")
except Exception as e:
    ok = False
    print(f"  FAIL {UNDERCLOUD_NETWORK_FILE} idempotency check: {e}")

# 24. Checks for the "duplicate hypervisor_if connection causes flip-flop" fix in
#     create_network_profiles.yml: the plain-ethernet task must now be gated on the
#     interface NOT already having an NM connection profile, so it only runs the
#     first time (not on every run alongside the bridge-port definition).
NETWORK_PROFILES_FILE = "roles/RHOSP-virt-infra/tasks/create_network_profiles.yml"
PLAIN_IFACE_TASK_NAME = "NETWORKING - Define hypervisor interfaces (first-run only, to adopt a previously-unmanaged NIC into NetworkManager)"
QUERY_NM_TASK_NAME = "NETWORKING - Get existing NetworkManager connection profile names"

try:
    with open(NETWORK_PROFILES_FILE) as fh:
        network_profiles_tasks = yaml.safe_load(fh)

    query_task = next(t for t in network_profiles_tasks if t.get("name") == QUERY_NM_TASK_NAME)
    if query_task.get("changed_when") is False and query_task.get("command") == "nmcli -t -f NAME connection show":
        print(f"  OK   {NETWORK_PROFILES_FILE}: '{QUERY_NM_TASK_NAME}' is a read-only NM connection list query")
    else:
        ok = False
        print(f"  FAIL {NETWORK_PROFILES_FILE}: '{QUERY_NM_TASK_NAME}' missing or malformed: {query_task}")

    plain_task = next(t for t in network_profiles_tasks if t.get("name") == PLAIN_IFACE_TASK_NAME)
    when_list = plain_task.get("when", [])
    has_first_run_guard = any("existing_nm_connections" in str(w) for w in when_list)
    if has_first_run_guard:
        print(f"  OK   {NETWORK_PROFILES_FILE}: '{PLAIN_IFACE_TASK_NAME}' is gated on first-run (not already an NM profile)")
    else:
        ok = False
        print(f"  FAIL {NETWORK_PROFILES_FILE}: '{PLAIN_IFACE_TASK_NAME}' missing the first-run guard: {when_list}")

    if jinja2 is None:
        print("  SKIP first-run guard logic test: jinja2 not installed")
    else:
        guard_expr = next(w for w in when_list if "existing_nm_connections" in str(w))
        env = make_env()
        compiled = env.compile_expression(guard_expr)

        fixtures = [
            ("first run, no existing profile", "enp17s0f0", [], True),
            ("subsequent run, profile already exists", "enp17s0f0", ["enp17s0f0", "br-ctlplane"], False),
            ("profile exists for a different interface only", "enp17s0f0", ["enp17s0f1"], True),
        ]
        for label, hyp_if, existing, expected in fixtures:
            result = bool(compiled(item={"hypervisor_if": hyp_if}, existing_nm_connections={"stdout_lines": existing}))
            if result == expected:
                print(f"  OK   first-run guard logic: {label}")
            else:
                ok = False
                print(f"  FAIL first-run guard logic: {label}: expected {expected}, got {result}")

except StopIteration:
    ok = False
    print(f"  FAIL {NETWORK_PROFILES_FILE}: expected tasks not found")
except Exception as e:
    ok = False
    print(f"  FAIL {NETWORK_PROFILES_FILE} first-run guard check: {e}")

# 25. Checks for the "needs_bios_image is undefined with --start-at-task TEMPLATES"
#     fix in roles/RHOSP-undercloud/tasks/main.yml: ironic_provisioned_machines /
#     needs_bios_image / needs_uefi_image must be re-registered after the TEMPLATES
#     restart point (they're only computed once, earlier, on a normal full run), and
#     the re-registration tasks must appear after TEMPLATES so --start-at-task
#     TEMPLATES actually reaches them.
RESTART_IMAGES_TASK_NAME = "IMAGES - Determine which director images are actually needed (again, for TEMPLATES restart)"
RESTART_BIOS_UEFI_TASK_NAME = "IMAGES - Determine BIOS/UEFI image requirements (again, for TEMPLATES restart)"

try:
    with open(UNDERCLOUD_MAIN_FILE) as fh:
        restart_tasks = yaml.safe_load(fh)
    names = [t.get("name") for t in restart_tasks]

    templates_idx = names.index("TEMPLATES")
    restart_images_idx = names.index(RESTART_IMAGES_TASK_NAME)
    restart_bios_uefi_idx = names.index(RESTART_BIOS_UEFI_TASK_NAME)

    if restart_images_idx > templates_idx and restart_bios_uefi_idx > templates_idx:
        print(f"  OK   {UNDERCLOUD_MAIN_FILE}: image-requirement facts are re-registered after TEMPLATES")
    else:
        ok = False
        print(
            f"  FAIL {UNDERCLOUD_MAIN_FILE}: image-requirement facts are not after TEMPLATES "
            f"(TEMPLATES={templates_idx}, images={restart_images_idx}, bios_uefi={restart_bios_uefi_idx})"
        )

    if jinja2 is None:
        print("  SKIP TEMPLATES-restart director image logic tests: jinja2 not installed")
    else:
        restart_images_task = restart_tasks[restart_images_idx]
        restart_bios_uefi_task = restart_tasks[restart_bios_uefi_idx]

        ironic_tmpl = restart_images_task["set_fact"]["ironic_provisioned_machines"]
        ironic_candidates_tmpl = restart_images_task["vars"]["ironic_candidates"]
        bios_tmpl = restart_bios_uefi_task["set_fact"]["needs_bios_image"]
        uefi_tmpl = restart_bios_uefi_task["set_fact"]["needs_uefi_image"]

        env = make_env()

        def compute_restart(libvirt_machines, physical_machines):
            ironic_candidates = yaml.safe_load(
                env.from_string(ironic_candidates_tmpl).render(
                    libvirt_machines=libvirt_machines, physical_machines=physical_machines
                )
            )
            ironic_provisioned = yaml.safe_load(
                env.from_string(ironic_tmpl).render(ironic_candidates=ironic_candidates)
            ) or []
            needs_bios = env.from_string(bios_tmpl).render(ironic_provisioned_machines=ironic_provisioned)
            needs_uefi = env.from_string(uefi_tmpl).render(ironic_provisioned_machines=ironic_provisioned)
            return len(ironic_provisioned), needs_bios == "True", needs_uefi == "True"

        fixtures = [
            ("one ironic bios machine", [machine(pre_provisioned=False, pm_mode="bios")], [], 1, True, False),
            ("one ironic uefi machine", [], [machine(pre_provisioned=False, pm_mode="uefi")], 1, False, True),
            ("all pre-provisioned (deployed servers)", [machine(pre_provisioned=True)], [], 0, False, False),
        ]
        for label, lm, pm, exp_count, exp_bios, exp_uefi in fixtures:
            count, got_bios, got_uefi = compute_restart(lm, pm)
            if count == exp_count and got_bios == exp_bios and got_uefi == exp_uefi:
                print(f"  OK   TEMPLATES-restart director image logic: {label}")
            else:
                ok = False
                print(
                    f"  FAIL TEMPLATES-restart director image logic: {label}: expected (count={exp_count}, "
                    f"bios={exp_bios}, uefi={exp_uefi}), got (count={count}, bios={got_bios}, uefi={got_uefi})"
                )

except ValueError as e:
    ok = False
    print(f"  FAIL {UNDERCLOUD_MAIN_FILE}: TEMPLATES-restart task(s) not found: {e}")
except Exception as e:
    ok = False
    print(f"  FAIL {UNDERCLOUD_MAIN_FILE} TEMPLATES-restart check: {e}")

sys.exit(0 if ok else 1)
