-- Keep only your personal keybinding overrides here. Add new bindings or
-- unbind defaults before replacing them.

-- See current bindings and descriptions:
--   omarchy menu keybindings --print

-- To disable every Omarchy default binding, set this in
-- ~/.config/hypr/hyprland.lua before require("default.hypr.omarchy"), then add
-- only the bindings you want below:
--   omarchy_default_bindings = false

-- To disable all preinstalled app/webapp bindings, set:
--   omarchy_preinstalled_bindings = false

-- Add a new binding.
-- o.bind("SUPER + SHIFT + R", "SSH", "alacritty -e ssh your-server")

-- Change an existing binding by unbinding it first, then binding the key again.
-- This example changes SUPER+SPACE from the launcher to the Omarchy root menu.
-- hl.unbind("SUPER + SPACE")
-- o.bind("SUPER + SPACE", "Omarchy menu", "omarchy-menu toggle root")

-- Disable a default binding without replacing it.
-- hl.unbind("SUPER + SHIFT + B")

-- Logitech MX Keys examples:
-- o.bind("SUPER + SHIFT + S", nil, "omarchy-capture-screenshot")
-- o.bind("SUPER + H", nil, "voxtype record toggle")
-- o.bind("SUPER + PERIOD", nil, "omarchy-shell shell toggle omarchy.emojis")

-- Button 5 always dictates. Commands use a separate explicit keyboard modifier.
hl.unbind("mouse:276")
o.bind("mouse:276", "Toggle dictation", voice_button5)
o.bind("SUPER + mouse:276", "Toggle explicit voice command", "python3 " .. os.getenv("HOME") .. "/.local/lib/voice-control/control.py command")


-- Button 4 stays independent of dictation/command routing.
-- Button 4 expands highlighted text into a task prompt; no selection sends Enter.
hl.unbind("mouse:275")
o.bind("mouse:275", "Voice button 4 down", voice_button4_down)
o.bind("mouse:275", "Voice button 4 release", voice_button4_up, { release = true })

-- Basilisk onboard F13: evdev 183 / XKB 191; layouts may name it XF86Tools.
o.bind("code:191", "Thumb paddle send", "wtype -k Return", { release = true })

-- taskgrid: collapse/expand the task overlay.
o.bind("SUPER + SHIFT + T", "Toggle TaskGrid", "@@HOME@@/.local/bin/taskgrid toggle")

-- Workspace picker shortcut; normal app right-click menus remain unchanged.
o.bind("ALT + mouse:273", "Move window to workspace 1-5", "@@HOME@@/.local/bin/tbm-workspace-menu")

-- Explicit number symbols: packaged code:10..19 bindings load as keycode 0
-- on this Hyprland build. Preserve the standard global workspace destinations.
for workspace = 1, 10 do
  local key = tostring(workspace % 10)
  local old_key = "code:" .. tostring(workspace + 9)
  for _, modifiers in ipairs({ "SUPER", "SUPER + SHIFT", "SUPER + SHIFT + ALT" }) do
    hl.unbind(modifiers .. " + " .. old_key)
    hl.unbind(modifiers .. " + " .. key)
  end
  o.bind("SUPER + " .. key, "Switch to workspace " .. workspace,
    hl.dsp.focus({ workspace = tostring(workspace) }))
  o.bind("SUPER + SHIFT + " .. key, "Move window to workspace " .. workspace,
    hl.dsp.window.move({ workspace = tostring(workspace) }))
  o.bind("SUPER + SHIFT + ALT + " .. key, "Move window silently to workspace " .. workspace,
    hl.dsp.window.move({ workspace = tostring(workspace), follow = false }))
end
