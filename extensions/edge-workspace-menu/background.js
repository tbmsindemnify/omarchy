const HOST = "com.tbm.workspace_menu";
async function installMenu() {
  await chrome.contextMenus.removeAll();
  chrome.contextMenus.create({id: "workspaces", title: "Move to workspace", contexts: ["all"]});
  for (let slot = 1; slot <= 5; slot++) {
    chrome.contextMenus.create({id: `workspace-${slot}`, parentId: "workspaces", title: `Workspace ${slot}`, contexts: ["all"]});
  }
}
chrome.runtime.onInstalled.addListener(installMenu);
chrome.runtime.onStartup.addListener(installMenu);
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const match = /^workspace-([1-5])$/.exec(String(info.menuItemId));
  if (!match || !tab) return;
  try {
    const browserWindow = await chrome.windows.get(tab.windowId);
    if (!browserWindow.focused) throw new Error("The clicked Edge window is no longer focused. Open its menu and try again.");
    const result = await chrome.runtime.sendNativeMessage(HOST, {
      action: "move", workspace: Number(match[1]), title: tab.title || ""
    });
    if (!result?.ok) throw new Error(result?.error || "Could not move this window.");
  } catch (error) {
    console.error("Workspace menu:", error);
    const message = encodeURIComponent(error.message || String(error));
    await chrome.tabs.create({url: chrome.runtime.getURL("error.html") + "?message=" + message});
  }
});
