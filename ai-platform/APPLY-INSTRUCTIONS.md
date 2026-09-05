# Applying the multi-model patch to ai-platform

## 1. Copy the 4 patched files over the originals

```bash
cd /mnt/c/Users/asadu/PROJECTS/shopnoltd/ai-platform/backend/app

cp /path/to/downloaded/config.py app/config.py    # actually: ai-platform/backend/app/config.py
cp /path/to/downloaded/client.py app/ai/client.py
cp /path/to/downloaded/tools.py app/ai/tools.py
cp /path/to/downloaded/engine.py app/ai/engine.py
```

(Adjust the source paths to wherever you save the 4 files from this chat —
they replace `backend/app/config.py`, `backend/app/ai/client.py`,
`backend/app/ai/tools.py`, `backend/app/ai/engine.py` exactly.)

## 2. Add litellm as a dependency

```bash
echo "litellm==1.52.0" >> ai-platform/backend/requirements.txt
```

## 3. Let the chat router accept a model choice (small edit, not a full file)

In `ai-platform/backend/app/routers/chat.py`, wherever it currently calls:

```python
reply_text, _ = run_conversation(claude_messages)
```

change to accept an optional `model` field from the request and pass it through:

```python
reply_text, _ = run_conversation(claude_messages, model=payload.model or DEFAULT_MODEL)
```

(import `DEFAULT_MODEL` from `app.ai.client`, and add `model: str | None = None`
to whatever Pydantic schema `payload` is.)

## 4. Add the new keys to the k8s Secret

```bash
kubectl -n shopno-platform get secret ai-platform-secret -o yaml > /tmp/ai-platform-secret-current.yaml
# inspect it, then patch in the new keys (base64-encode each value first: echo -n "sk-..." | base64 -w0)
kubectl -n shopno-platform patch secret ai-platform-secret --type merge -p \
  '{"data":{"OPENAI_API_KEY":"<base64>","GEMINI_API_KEY":"<base64>"}}'
```

Also add the equivalent to wherever this Secret is defined in your GitOps repo
(likely a sealed-secret or external-secret reference, not plaintext — check
`k8s/services/ai-platform/` for how `ai-platform-secret` is actually sourced)
so it doesn't drift on the next ArgoCD sync.

## 5. Rebuild and roll out

Your image is `ghcr.io/asaduzzamanbheramara-prog/shopnoltd/ai-platform:latest`
with `imagePullPolicy: IfNotPresent` — on a single-node cluster this means a
plain `rollout restart` may reuse the cached image and NOT pick up your new
code. After your GitHub Actions build pushes the new `:latest`:

```bash
kubectl -n shopno-platform delete pod -l app.kubernetes.io/name=ai-platform
```

(Deleting the pod forces a fresh pull attempt via the same mechanism as
restart, but if k3s still has the old `:latest` layer cached locally this
still won't refetch. Safest long-term fix: tag images with the git SHA in CI
and reference that tag in `deployment.yaml` instead of `:latest` — happy to
help set that up if you want.)

## 6. Test

```bash
curl -s https://api.shopnoltd.dpdns.org/chat/sessions/<id>/messages \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "what time is it", "model": "gpt-4o"}'
```

Try `"model": "claude-sonnet"` and `"model": "gemini-flash"` too, to confirm
all three routes actually work.

---

## Code-server AI integration

The standalone LiteLLM proxy previously described here has been removed because
it is not used by the current `ai-platform` implementation and duplicates the
LiteLLM dependency already used as a Python library.

For the free local coding-assistant path, use the existing Ollama deployment in
`shopno-apps` instead of maintaining a second always-on LiteLLM proxy.
