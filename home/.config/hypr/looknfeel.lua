-- Change the default Omarchy look'n'feel.

-- https://wiki.hypr.land/Configuring/Basics/Variables/#general
-- hl.config({
--   general = {
--     -- No gaps between windows or borders.
--     gaps_in = 0,
--     gaps_out = 0,
--     border_size = 0,
--
--     -- Change to niri-like side-scrolling layout.
--     layout = "scrolling",
--   },
-- })

-- https://wiki.hypr.land/Configuring/Basics/Variables/#decoration
-- hl.config({
--   decoration = {
--     -- Use round window corners.
--     rounding = 8,
--
--     -- Dim unfocused windows (0.0 = no dim, 1.0 = fully dimmed).
--     dim_inactive = true,
--     dim_strength = 0.15,
--   },
-- })

-- https://wiki.hypr.land/Configuring/Basics/Variables/#animations
-- hl.config({
--   animations = {
--     -- Disable all animations.
--     enabled = false,
--   },
-- })

-- https://wiki.hypr.land/Configuring/Basics/Variables/#layout
-- hl.config({
--   layout = {
--     -- Avoid overly wide single-window layouts on wide screens.
--     single_window_aspect_ratio = { 1, 1 },
--   },
-- })

-- https://wiki.hypr.land/Configuring/Layouts/Scrolling-Layout/
-- hl.config({
--   scrolling = {
--     -- See only one column per screen instead of two.
--     column_width = 0.97,
--   },
-- })

-- Make the focused window obvious when moving focus (SUPER + arrows):
-- thick bright border on the active window, thin dark border + dimming on the rest.
hl.config({
  general = {
    border_size = 5,
    col = {
      active_border = { colors = { "rgba(ff0055ff)", "rgba(ffcc00ff)", "rgba(00ff99ff)", "rgba(00ccffff)", "rgba(aa00ffff)", "rgba(ff0055ff)" }, angle = 45 },
      inactive_border = "rgba(333333aa)",
    },
  },
  decoration = {
    dim_inactive = true,
    dim_strength = 0.25,
  },
})

-- Spin the active border's rainbow gradient around the window continuously.
hl.animation({ leaf = "borderangle", enabled = true, speed = 15, bezier = "linear", style = "loop" })
