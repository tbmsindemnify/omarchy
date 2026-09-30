-- Capture actual configured actions, so voice commands follow keyboard updates.
-- Loaded after helpers, before the default bindings are registered.
voice_actions = {}
local original_bind = o.bind
function o.bind(keys, description, dispatcher, options)
  original_bind(keys, description, dispatcher, options)
  local opts = options or {}
  if description and not opts.release and not opts.mouse then
    -- Reuse Omarchy's conversion for launcher shorthand through a temporary
    -- hl.bind wrapper; capture the final dispatcher rather than reimplement it.
    local real_bind = hl.bind
    hl.bind = function(_, action) voice_actions[description] = action end
    local ok, err = pcall(original_bind, keys, description, dispatcher, options)
    hl.bind = real_bind
    if not ok then error(err) end
  end
end
function voice_run(description)
  local action = voice_actions[description]
  if not action then error("Voice action unavailable: " .. description) end
  hl.dispatch(action)
end

-- Button 4 rewrites selected text or sends Enter, unless used for a command chord.
voice_mouse4_held = false
voice_mouse4_used = false
function voice_button4_down()
  voice_mouse4_held = true
  voice_mouse4_used = false
end
function voice_button4_up()
  local send = voice_mouse4_held and not voice_mouse4_used
  voice_mouse4_held = false
  voice_mouse4_used = false
  if send then hl.dispatch(hl.dsp.exec_cmd("python3 " .. os.getenv("HOME") .. "/.local/lib/voice-control/prompt_selection.py")) end
end
function voice_button5()
  -- Button 5 must never inherit stale state from another mouse button.
  if voice_mouse4_held then voice_mouse4_used = true end
  hl.dispatch(hl.dsp.exec_cmd("python3 " .. os.getenv("HOME") .. "/.local/lib/voice-control/control.py dictate"))
end
