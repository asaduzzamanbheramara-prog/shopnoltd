import re
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.core.reserved import RESERVED

PARENT = ".shopnoltd.dpdns.org"
HOST_LINE = re.compile(r"""^\s*(?:-\s*)?host:\s*["']?([^"'\s]+)["']?\s*$""")
DNS_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
ROLE_NAMES = ("postmaster", "abuse", "hostmaster", "webmaster", "noc", "security")


def ingress_labels():
    labels = set()
    for pattern in ("*.yaml", "*.yml"):
        for path in (REPO_ROOT / "k8s").rglob(pattern):
            for line in path.read_text(encoding="utf-8").splitlines():
                match = HOST_LINE.match(line)
                if not match:
                    continue
                host = match.group(1).lower()
                if host.startswith("*") or not host.endswith(PARENT):
                    continue
                labels.add(host[: -len(PARENT)].split(".")[-1])
    return labels


def test_scan_finds_the_platform_ingress_hosts():
    # Guards against the scan silently matching nothing.
    assert len(ingress_labels()) >= 10


def test_every_platform_ingress_label_is_reserved():
    missing = sorted(ingress_labels() - RESERVED)
    assert not missing, f"Add these ingress labels to RESERVED: {missing}"


def test_mailbox_role_names_are_reserved():
    assert set(ROLE_NAMES) <= RESERVED


def test_reserved_labels_are_valid_dns_labels():
    bad = sorted(label for label in RESERVED if not DNS_LABEL.match(label))
    assert not bad, f"Invalid labels: {bad}"
