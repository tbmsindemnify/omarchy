-- Learn how to configure Hyprland: https://wiki.hypr.land/Configuring/Start/

-- Omarchy's bootstrap keeps path setup out of this user config.
dofile((os.getenv("OMARCHY_PATH") or "/usr/share/omarchy") .. "/default/hypr/bootstrap.lua")

-- Disable all Omarchy default bindings. Add your own in hypr/bindings.lua.
-- omarchy_default_bindings = false
--
-- Or disable only bindings for Omarchy's preinstalled apps/web apps while
-- keeping core window-manager bindings:
-- omarchy_preinstalled_bindings = false

-- Capture keyboard actions for the local voice command catalog.
require("default.hypr.helpers")
require("hypr.voice-registry")

-- Load Omarchy defaults.
require("default.hypr.omarchy")

-- Put your personal overrides in these files. They're loaded after Omarchy's
-- defaults so package updates can improve the defaults without rewriting your
-- ~/.config/hypr files.
require("hypr.monitors")
require("hypr.input")
require("hypr.bindings")
require("hypr.looknfeel")
require("hypr.autostart")

-- Toggle config flags dynamically.
require("default.hypr.toggles")

-- Add any other personal Hyprland configuration below.
-- o.window("qemu", { workspace = "5" })


-- Keeper app opens on workspace 4.
o.window("^msedge-keepersecurity[.]com__vault_-Profile_2$", { workspace = "4 silent" })

-- Machine-specific monitor/workspace rules are generated during installation.
require("hypr.tbm-machine")

-- Keep the chat app on workspace 3 without stealing focus.
o.window("^chatgpt$", { workspace = "3 silent", focus_on_activate = false })

-- Keep the VM flush with the reserved sidebar.
hl.workspace_rule({ workspace = "2", gaps_in = 0, gaps_out = 0, no_border = true, no_rounding = true })
