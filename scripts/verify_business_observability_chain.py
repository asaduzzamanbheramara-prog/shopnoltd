#!/usr/bin/env python3
"""Static verification for the HR/POS/ERP -> observability GitOps chain.

This intentionally checks repository structure only; live cluster health remains the
responsibility of the post-deployment smoke workflow.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
required_any = {
    "HR/POS/ERP website types": [
        ROOT / "platform/web-portal/src/lib/websiteTypes.js",
    ],
    "Kubernetes manifests": [ROOT / "k8s"],
    "CI workflows": [ROOT / ".github/workflows"],
}

required_terms = {
    ROOT / "platform/web-portal/src/lib/websiteTypes.js": ["hr", "pos", "pos_billing", "erp"],
    ROOT / ".github/workflows/post-deployment-smoke.yml": ["workflow_run", "healthz", "billing", "payment", "exchange"],
}

errors = []
for label, paths in required_any.items():
    if not any(p.exists() for p in paths):
        errors.append(f"missing: {label}")

for path, terms in required_terms.items():
    if not path.exists():
        errors.append(f"missing file: {path.relative_to(ROOT)}")
        continue
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    for term in terms:
        if term.lower() not in text:
            errors.append(f"missing term '{term}' in {path.relative_to(ROOT)}")

# Confirm observability resources exist somewhere under k8s.
k8s_text = "\n".join(
    p.read_text(encoding="utf-8", errors="replace")
    for p in (ROOT / "k8s").rglob("*")
    if p.is_file() and p.suffix in {".yaml", ".yml", ".json", ".md"}
).lower()
for term in ("prometheus", "grafana", "alertmanager"):
    if term not in k8s_text:
        errors.append(f"missing observability reference: {term}")

if errors:
    print("BUSINESS/OBSERVABILITY CHAIN VERIFICATION FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("BUSINESS/OBSERVABILITY CHAIN STATIC VERIFICATION PASSED")
