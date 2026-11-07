// Service worker: keeps a WebSocket to the agent service and executes browser commands.
// Safety model:
//  - The agent can only operate tabs IT opened (or tabs you attach from the popup), never your other tabs.
//  - Every command re-checks that you granted this extension access to the tab's site.
//  - Only http(s) URLs. Password fields are never typed into. Typed text is not logged.
//  - Every action is logged to chrome.storage.local ("log", last 200).
const AGENT_WS = "wss://agent.shopnoltd.dpdns.org/ws/ext";  // change to your deployed URL
const MAX_LOG = 200;
let ws = null;
let authed = false;
let keepAlive = null;

// ---------- agent tab registry (survives service-worker restarts) ----------
async function agentTabs() {
  const { tabs = [] } = await chrome.storage.session.get("tabs");
  return tabs;
}
async function addAgentTab(id) {
  const tabs = await agentTabs();
  if (!tabs.includes(id)) tabs.push(id);
  await chrome.storage.session.set({ tabs, last: id });
}
chrome.tabs.onRemoved.addListener(async (id) => {
  const tabs = (await agentTabs()).filter((t) => t !== id);
  const { last } = await chrome.storage.session.get("last");
  await chrome.storage.session.set({ tabs, last: last === id ? tabs[tabs.length - 1] : last });
});

// ---------- log ----------
async function log(entry) {
  const { log = [] } = await chrome.storage.local.get("log");
  log.push({ t: Date.now(), ...entry });
  await chrome.storage.local.set({ log: log.slice(-MAX_LOG) });
}

// ---------- connection ----------
function connect(token) {
  if (ws) ws.close();
  authed = false;
  if (keepAlive) clearInterval(keepAlive);
  ws = new WebSocket(AGENT_WS);  // token is sent as the first message, never in the URL
  ws.onopen = () => ws.send(JSON.stringify({ type: "auth", token }));
  ws.onmessage = async (e) => {
    let cmd;
    try { cmd = JSON.parse(e.data); } catch { return; }
    if (cmd.type === "auth_ok") { authed = true; return; }
    if (!authed || !cmd.id) return;
    let out;
    try { out = { id: cmd.id, ok: true, ...(await run(cmd)) }; }
    catch (err) {
      await log({ action: cmd.action, ok: false, error: String(err).slice(0, 200) });
      out = { id: cmd.id, ok: false, error: String(err) };
    }
    ws && ws.readyState === 1 && ws.send(JSON.stringify(out));
  };
  ws.onclose = () => { ws = null; authed = false; if (keepAlive) clearInterval(keepAlive); };
  keepAlive = setInterval(() => ws && ws.readyState === 1 && ws.send(JSON.stringify({ ping: 1 })), 20000);
}

// ---------- helpers ----------
function isHttp(url) {
  try { return /^https?:$/.test(new URL(url).protocol); } catch { return false; }
}
async function siteAllowed(url) {
  try {
    const u = new URL(url);
    if (!/^https?:$/.test(u.protocol)) return false;
    return await chrome.permissions.contains({ origins: [u.origin + "/*"] });
  } catch { return false; }
}
async function waitLoad(tabId, ms = 15000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    const t = await chrome.tabs.get(tabId);
    if (t.status === "complete") return;
    await new Promise((r) => setTimeout(r, 300));
  }
}
async function inPage(tabId, fn, args) {
  const [r] = await chrome.scripting.executeScript({ target: { tabId }, func: fn, args });
  return r.result;
}

async function run(cmd) {
  if (cmd.action === "open") {
    if (!isHttp(cmd.url)) throw new Error("only http(s) URLs");
    const t = await chrome.tabs.create({ url: cmd.url });
    await addAgentTab(t.id);
    await waitLoad(t.id);
    const t2 = await chrome.tabs.get(t.id);
    await log({ action: "open", host: new URL(t2.url || cmd.url).host, ok: true });
    return { tabId: t.id, url: t2.url };
  }

  const { last } = await chrome.storage.session.get("last");
  const tabId = cmd.tabId ?? last;
  if (tabId == null) throw new Error("no agent tab: use open first");
  if (!(await agentTabs()).includes(tabId)) throw new Error("not an agent tab");
  const tab = await chrome.tabs.get(tabId);   // throws if closed
  if (!(await siteAllowed(tab.url))) {
    throw new Error("site not approved: ask the user to grant this extension access to " + new URL(tab.url).origin);
  }
  const host = new URL(tab.url).host;

  switch (cmd.action) {
    case "get_text": {
      const text = await inPage(tabId, () => document.body.innerText.slice(0, 20000), []);
      await log({ action: "get_text", host, ok: true });
      return { url: tab.url, text };
    }
    case "click": {
      const clicked = await inPage(tabId, (sel) => {
        const el = document.querySelector(sel); if (!el) return false; el.click(); return true;
      }, [String(cmd.selector).slice(0, 500)]);
      await log({ action: "click", host, selector: String(cmd.selector).slice(0, 100), ok: clicked });
      return { clicked };
    }
    case "type": {
      const r = await inPage(tabId, (sel, txt) => {
        const el = document.querySelector(sel); if (!el) return "not_found";
        if (el.type === "password") return "password_blocked";
        el.focus();
        if (el.isContentEditable) {
          el.textContent = txt;
          el.dispatchEvent(new InputEvent("input", { bubbles: true }));
          return "ok";
        }
        const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
        if (!setter) return "not_typable";
        setter.call(el, txt);                       // works with React/Vue controlled inputs
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
        return "ok";
      }, [String(cmd.selector).slice(0, 500), String(cmd.text).slice(0, 5000)]);
      await log({ action: "type", host, selector: String(cmd.selector).slice(0, 100), chars: String(cmd.text).length, ok: r === "ok" });
      if (r !== "ok") throw new Error("type failed: " + r);
      return { typed: true };
    }
    case "scroll":
      await inPage(tabId, () => window.scrollBy(0, window.innerHeight * 0.8), []);
      await log({ action: "scroll", host, ok: true });
      return { scrolled: true };
    case "screenshot": {
      await chrome.tabs.update(tabId, { active: true });   // captureVisibleTab shoots the active tab
      const image = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "jpeg", quality: 60 });
      await log({ action: "screenshot", host, ok: true });
      return { image };
    }
    default:
      throw new Error("unknown action");
  }
}

// ---------- messages from the popup only ----------
chrome.runtime.onMessage.addListener((m, sender, reply) => {
  if (sender.id !== chrome.runtime.id) return;
  if (m.type === "connect") { connect(m.token); reply({ status: "connecting" }); }
  else if (m.type === "disconnect") { ws && ws.close(); reply({ status: "disconnected" }); }
  else if (m.type === "status") reply({ status: ws && ws.readyState === 1 && authed ? "connected" : (ws ? "connecting" : "disconnected") });
  else if (m.type === "attach") {   // popup: let the agent work in the tab you are looking at
    chrome.tabs.query({ active: true, currentWindow: true }).then(async ([t]) => {
      if (t) await addAgentTab(t.id);
      reply({ attached: t ? t.id : null });
    });
    return true;
  }
  else if (m.type === "log") chrome.storage.local.get("log").then((r) => reply({ log: r.log || [] })), true;
  return true;
});
