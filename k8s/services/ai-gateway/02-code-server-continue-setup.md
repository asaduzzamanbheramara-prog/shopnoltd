# Wiring code-server to LiteLLM

## 1. Install the Continue extension into your code-server pod

code-server's built-in Marketplace is disabled by default, so install from Open VSX instead:

```bash
POD=$(kubectl -n shopno-ai get pod -l app.kubernetes.io/name=code-server -o jsonpath='{.items[0].metadata.name}')
kubectl -n shopno-ai exec "$POD" -- code-server --install-extension continue.continue
```

(If your code-server deployment lives in a different namespace, e.g. `shopno-apps`, swap it in.)

## 2. Drop this config where Continue expects it

Continue reads `~/.continue/config.json` inside the code-server container's home dir
(usually a PVC-backed path so it survives restarts — check your code-server
deployment's volumeMounts for something like `/home/coder`).

Write this file to `/tmp/continue-config.json` first (per your known WSL2 heredoc-corruption
issue — use a Python script to write it, not a direct terminal paste), then copy it in:

```python
# /tmp/write_continue_config.py
import json
config = {
    "models": [
        {
            "title": "Claude Sonnet (via LiteLLM)",
            "provider": "openai",
            "model": "claude-sonnet",
            "apiBase": "https://openai.shopnoltd.dpdns.org/v1",
            "apiKey": "sk-litellm-REPLACE_ME"
        },
        {
            "title": "GPT-4o (via LiteLLM)",
            "provider": "openai",
            "model": "gpt-4o",
            "apiBase": "https://openai.shopnoltd.dpdns.org/v1",
            "apiKey": "sk-litellm-REPLACE_ME"
        },
        {
            "title": "Gemini Flash (via LiteLLM)",
            "provider": "openai",
            "model": "gemini-flash",
            "apiBase": "https://openai.shopnoltd.dpdns.org/v1",
            "apiKey": "sk-litellm-REPLACE_ME"
        }
    ],
    "tabAutocompleteModel": {
        "title": "GPT-4o (via LiteLLM)",
        "provider": "openai",
        "model": "gpt-4o",
        "apiBase": "https://openai.shopnoltd.dpdns.org/v1",
        "apiKey": "sk-litellm-REPLACE_ME"
    }
}
with open("/tmp/continue-config.json", "w") as f:
    json.dump(config, f, indent=2)
```

Run it, then copy into the pod:

```bash
python3 /tmp/write_continue_config.py

kubectl -n shopno-ai exec "$POD" -- mkdir -p /home/coder/.continue
kubectl -n shopno-ai cp /tmp/continue-config.json "$POD":/home/coder/.continue/config.json
```

Replace `sk-litellm-REPLACE_ME` with the `LITELLM_MASTER_KEY` value you set in
`01-litellm-proxy.yaml`'s Secret — it's the ONE key code-server needs; the actual
OpenAI/Anthropic/Gemini keys stay only inside the LiteLLM pod.

## 3. Verify

```bash
# from your WSL2 shell, confirm the proxy answers and lists your models
curl -s https://openai.shopnoltd.dpdns.org/v1/models \
  -H "Authorization: Bearer sk-litellm-REPLACE_ME" | jq .

# then in code-server: open the Continue side panel (Ctrl+L), pick a model
# from the dropdown, and send a test prompt
```

## 4. Commit, don't just kubectl apply

Since you run ArgoCD GitOps, put `01-litellm-proxy.yaml` into your
`asaduzzamanbheramara-prog/shopnoltd` repo under the appropriate kustomize path,
commit, and let ArgoCD sync it — applying directly against the live cluster only
will drift on the next sync, per your existing kustomize-drift issue.
