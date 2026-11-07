const s = document.getElementById("s");
document.getElementById("c").onclick = () => {
  chrome.runtime.sendMessage({ type: "connect", token: document.getElementById("t").value }, r => s.textContent = r?.status || "error");
};
document.getElementById("d").onclick = () => chrome.runtime.sendMessage({ type: "disconnect" }, r => s.textContent = r?.status || "error");
chrome.runtime.sendMessage({ type: "status" }, r => s.textContent = r?.status || "disconnected");
