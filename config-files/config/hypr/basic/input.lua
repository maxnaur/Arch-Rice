---------------
---- INPUT ----
---------------

-- input devices
-- hyprctl devices

-- keybord and mouse default
hl.config({
	input = {
		kb_layout = "gb",
		kb_variant = "",
		kb_model = "",
		kb_options = "",
		kb_rules = "",

		follow_mouse = 1, -- when mouse move hilight the tab you are on

		sensitivity = -0.2, -- -1.0 - 1.0, 0 means no modification.
		force_no_accel = true,
		natural_scroll = false,

		touchpad = {
			disable_while_typing = true,
			natural_scroll = true,
			tap_to_click = true, -- 1 click, 2 right cleck, 3 midle click
			--drag_3fg = 2, -- 4 finger drag bettween workspace
		},
	},
})

hl.gesture({
	fingers = 4,
	direction = "horizontal",
	action = "workspace",
})

-- Example per-device config
--[[hl.device({
	name           = "epic-mouse-v1",
	sensitivity    = -0.2,
  force_no_accel = false,
  natural_scroll = true,
})]]
