/* global chrome, PLATFORMS */

const $ = (id) => document.getElementById(id);

let currentPlatform = null;
let currentTabUrl = "";

// --- Storage helpers ---

async function loadConfig() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["backendUrl", "pairingToken"], resolve);
  });
}

async function saveConfig(backendUrl, pairingToken) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ backendUrl, pairingToken }, resolve);
  });
}

// --- Platform detection ---

function detectPlatform(url) {
  for (const [key, platform] of Object.entries(PLATFORMS)) {
    if (platform.match.test(url)) {
      return { key, ...platform };
    }
  }
  return null;
}

// --- Cookie extraction ---

async function extractCookies(platform) {
  const allCookies = [];
  for (const domain of platform.domains) {
    const cookies = await chrome.cookies.getAll({ domain });
    allCookies.push(...cookies);
  }
  // Deduplicate by name (prefer longer domain match)
  const seen = new Map();
  for (const c of allCookies) {
    if (!seen.has(c.name) || c.domain.length > seen.get(c.name).domain.length) {
      seen.set(c.name, c);
    }
  }
  // Return as name→value dict for simplicity
  const result = {};
  for (const [name, cookie] of seen) {
    result[name] = cookie.value;
  }
  return result;
}

// --- API call ---

async function syncToBackend(backendUrl, pairingToken, platformKey, cookies) {
  const url = `${backendUrl.replace(/\/+$/, "")}/api/extensions/sync-session/`;
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Extension-Token": pairingToken,
    },
    body: JSON.stringify({
      platform: platformKey,
      cookies,
    }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status}: ${text}`);
  }
  return resp.json();
}

// --- UI helpers ---

function showStatus(el, type, msg) {
  el.className = `status ${type}`;
  el.textContent = msg;
  el.style.display = "block";
}

const PLATFORM_ICONS = {
  twitter: "𝕏",
  reddit: "📡",
  luma: "✦",
};

// --- Init ---

async function init() {
  const config = await loadConfig();
  const backendUrl = config.backendUrl || "";
  const pairingToken = config.pairingToken || "";

  $("backendUrl").value = backendUrl;
  $("pairingToken").value = pairingToken;

  const isConfigured = backendUrl && pairingToken;
  $("statusDot").classList.toggle("connected", isConfigured);

  if (isConfigured) {
    $("syncSection").style.display = "block";
  }

  // Detect current tab's platform
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.url) {
    currentTabUrl = tab.url;
    currentPlatform = detectPlatform(tab.url);
  }

  if (currentPlatform) {
    const icon = PLATFORM_ICONS[currentPlatform.key] || "🌐";
    $("platformInfo").innerHTML = `
      <div class="platform-badge">
        <span class="icon">${icon}</span>
        <span>${currentPlatform.label}</span>
      </div>
    `;
    $("syncBtn").disabled = !isConfigured;
  } else {
    $("platformInfo").innerHTML = `
      <div class="no-platform">
        Navigate to a supported site to sync cookies.<br>
        <span style="color:#555; font-size:11px; margin-top:4px; display:block;">
          ${Object.values(PLATFORMS).map((p) => p.label).join(" · ")}
        </span>
      </div>
    `;
    $("syncBtn").disabled = true;
  }
}

// --- Event handlers ---

$("saveConfigBtn").addEventListener("click", async () => {
  const backendUrl = $("backendUrl").value.trim();
  const pairingToken = $("pairingToken").value.trim();

  if (!backendUrl || !pairingToken) {
    showStatus($("setupStatus"), "error", "Both fields are required");
    return;
  }

  await saveConfig(backendUrl, pairingToken);
  showStatus($("setupStatus"), "success", "Saved");
  $("statusDot").classList.add("connected");
  $("syncSection").style.display = "block";

  if (currentPlatform) {
    $("syncBtn").disabled = false;
  }
});

$("syncBtn").addEventListener("click", async () => {
  if (!currentPlatform) return;

  $("syncBtn").disabled = true;
  $("syncBtn").textContent = "Syncing...";
  $("syncStatus").style.display = "none";

  try {
    const config = await loadConfig();
    const cookies = await extractCookies(currentPlatform);
    const count = Object.keys(cookies).length;

    if (count === 0) {
      showStatus($("syncStatus"), "error", "No cookies found. Are you logged in?");
      return;
    }

    const result = await syncToBackend(
      config.backendUrl,
      config.pairingToken,
      currentPlatform.key,
      cookies,
    );

    showStatus(
      $("syncStatus"),
      "success",
      `Synced ${count} cookies for ${currentPlatform.label} → ${result.agent_name || "agent"}`,
    );
  } catch (e) {
    showStatus($("syncStatus"), "error", e.message);
  } finally {
    $("syncBtn").disabled = false;
    $("syncBtn").textContent = "Sync Cookies";
  }
});

init();
