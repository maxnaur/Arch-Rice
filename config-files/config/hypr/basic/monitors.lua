------------------
---- MONITORS ----
------------------

-- See https://wiki.hypr.land/Configuring/Basics/Monitors/
-- hyprctl monitors all

-- laptop screen
hl.monitor({
	output = "monitor:eDP-1",
	mode = "2560x1600@240",
	position = "0x0",
	scale = "2",
})
hl.workspace_rule({ workspace = "1", default_name = "🐵", monitor = "eDP-1", default = true })
hl.workspace_rule({ workspace = "2", default_name = "🦊", monitor = "eDP-1" })
hl.workspace_rule({ workspace = "3", default_name = "🐻", monitor = "eDP-1" })
hl.workspace_rule({ workspace = "4", default_name = "🐼", monitor = "eDP-1" })

-- acer or amazon monitor screen
hl.monitor({
	output = "monitor:HDMI-A-1",
	mode = "1920x1080@60",
	position = "auto",
	scale = "1",
})
hl.workspace_rule({ workspace = "5", default_name = "🍿", monitor = "HDMI-A-1", monitor = "DP-2", default = true })
hl.workspace_rule({ workspace = "6", default_name = "💬", monitor = "HDMI-A-1" })
hl.workspace_rule({ workspace = "7", default_name = "🎷", monitor = "HDMI-A-1" })

-- Uni monitor screen (on usb port)
hl.monitor({
	output = "monitor:DP-2",
	mode = "2560x1440@60",
	position = "auto",
	scale = "1.5",
})

-- second screen will be on the right side
hl.monitor({
	output = "",
	mode = "preferred",
	position = "auto",
	scale = "auto",
})

-- Lid Shut
