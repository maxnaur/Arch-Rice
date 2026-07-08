-----------------------
---- LOOK AND FEEL ----
-----------------------

-- import the colours
local colors = require("themes.catppuccin-frappe") --mocha")

-- Non-alpha values are already in Hyprland's rgb(...) format.
--local base = colors.base

-- Alpha variants
local surface0 = "rgba(" .. colors.baseAlpha .. "aa)"
local surface1 = "rgba(" .. colors.surface1Alpha .. "ee)"
local subtext0 = "rgba(" .. colors.subtext0Alpha .. "ee)"
local subtext1 = "rgba(" .. colors.subtext1Alpha .. "ee)"
local blue_ee = "rgba(" .. colors.blueAlpha .. "ee)"
local green_ee = "rgba(" .. colors.greenAlpha .. "ee)"
local mantle_ee = "rgba(" .. colors.mantleAlpha .. "ee)"

-- Refer to https://wiki.hypr.land/Configuring/Basics/Variables/
hl.config({
	general = {
		gaps_in = 4,
		gaps_out = 5,

		border_size = 2,

		col = {
			active_border = {
				colors = {
					blue_ee,
					subtext0,
					subtext1,
					green_ee,
				},
				angle = 45,
			},
			inactive_border = surface0,
		},

		-- Same as windows but ressets if an item is moved (i like that)
		resize_on_border = true,

		-- not doing it and just gameing on windows because nvidia is real dificalt
		-- Please see https://wiki.hypr.land/Configuring/Advanced-and-Cool/Tearing/ before you turn this on
		allow_tearing = false,

		-- "dwindle"/"master"/"scrolling"/"monocle"
		layout = "dwindle",

		-- floating windows
		snap = {
			enabled = false,
		},
	},

	decoration = {
		rounding = 5,
		rounding_power = 3,

		-- Change transparency of focused and unfocused windows
		active_opacity = 1.0,
		inactive_opacity = 1.0, -- still debating if this is good or not and needs some fire wallpapers
		fullscreen_opacity = 1,
		dim_around = 0.4,

		-- dim
		dim_modal = false,
		dim_inactive = false,
		dim_strength = 0.5,
		dim_special = 0.2,

		shadow = {
			enabled = true,
			range = 4,
			render_power = 3,
			color = mantle_ee,
		},

		blur = {
			enabled = true,
			size = 3,
			passes = 1,
			vibrancy = 0.1696,
		},

		border_part_of_window = false,
	},

	animations = {
		enabled = true,
		workspace_wraparound = false,
	},
})

-- Default curves and animations, see https://https://wiki.hypr.land/Configuring/Advanced-and-Cool/Animations/
hl.curve("easeOutQuint", { type = "bezier", points = { { 0.23, 1 }, { 0.32, 1 } } })
hl.curve("easeInOutCubic", { type = "bezier", points = { { 0.65, 0.05 }, { 0.36, 1 } } })
hl.curve("linear", { type = "bezier", points = { { 0, 0 }, { 1, 1 } } })
hl.curve("almostLinear", { type = "bezier", points = { { 0.5, 0.5 }, { 0.75, 1 } } })
hl.curve("quick", { type = "bezier", points = { { 0.15, 0 }, { 0.1, 1 } } })

-- Default springs
hl.curve("easy", { type = "spring", mass = 1, stiffness = 71.2633, dampening = 15.8273644 })

hl.animation({ leaf = "global", enabled = true, speed = 10, bezier = "default" })
hl.animation({ leaf = "border", enabled = true, speed = 5.39, bezier = "easeOutQuint" })
hl.animation({ leaf = "windows", enabled = true, speed = 4.79, spring = "easy" })
hl.animation({ leaf = "windowsIn", enabled = true, speed = 4.1, spring = "easy", style = "popin 87%" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 1.49, bezier = "linear", style = "popin 87%" })
hl.animation({ leaf = "fadeIn", enabled = true, speed = 1.73, bezier = "almostLinear" })
hl.animation({ leaf = "fadeOut", enabled = true, speed = 1.46, bezier = "almostLinear" })
hl.animation({ leaf = "fade", enabled = true, speed = 3.03, bezier = "quick" })
hl.animation({ leaf = "layers", enabled = true, speed = 3.81, bezier = "easeOutQuint" })
hl.animation({ leaf = "layersIn", enabled = true, speed = 4, bezier = "easeOutQuint", style = "fade" })
hl.animation({ leaf = "layersOut", enabled = true, speed = 1.5, bezier = "linear", style = "fade" })
hl.animation({ leaf = "fadeLayersIn", enabled = true, speed = 1.79, bezier = "almostLinear" })
hl.animation({ leaf = "fadeLayersOut", enabled = true, speed = 1.39, bezier = "almostLinear" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 1.94, bezier = "almostLinear", style = "fade" })
hl.animation({ leaf = "workspacesIn", enabled = true, speed = 1.21, bezier = "almostLinear", style = "fade" })
hl.animation({ leaf = "workspacesOut", enabled = true, speed = 1.94, bezier = "almostLinear", style = "fade" })
hl.animation({ leaf = "zoomFactor", enabled = true, speed = 7, bezier = "quick" })

-- Ref https://wiki.hypr.land/Configuring/Basics/Workspace-Rules/
-- "Smart gaps" / "No gaps when only"
-- uncomment all if you wish to use that.
-- hl.workspace_rule({ workspace = "w[tv1]", gaps_out = 0, gaps_in = 0 })
-- hl.workspace_rule({ workspace = "f[1]",   gaps_out = 0, gaps_in = 0 })
-- hl.window_rule({
--     name  = "no-gaps-wtv1",
--     match = { float = false, workspace = "w[tv1]" },
--     border_size = 0,
--     rounding    = 0,
-- })
-- hl.window_rule({
--     name  = "no-gaps-f1",
--     match = { float = false, workspace = "f[1]" },
--     border_size = 0,
--     rounding    = 0,
-- })

hl.config({
	-- See https://wiki.hypr.land/Configuring/Layouts/Dwindle-Layout/
	dwindle = {
		preserve_split = true, -- You probably want this
	},
	-- See https://wiki.hypr.land/Configuring/Layouts/Master-Layout/
	master = {
		new_status = "master",
	},
	-- See https://wiki.hypr.land/Configuring/Layouts/Scrolling-Layout/
	scrolling = {
		fullscreen_on_one_column = true,
	},

	----------------
	----  MISC  ----
	----------------

	misc = {
		disable_hyprland_logo = true, -- remove walpaper
		disable_splash_rendering = true, -- remove walpaper messaged
		font_family = "lexend", -- font
		allow_session_lock_restore = true, -- need for screen lock (need to set up before uni!)
		background_color = surface0,
	},
})
