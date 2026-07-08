------------------
---- MONITORS ----
------------------

-- See https://wiki.hypr.land/Configuring/Basics/Monitors/
--

-- laptop screen
hl.monitor({
	output = "monitor:eDP-1",
	mode = "2560x1600@240",
	position = "0x0",
	scale = "2",
})
hl.workspace_rule({ workspace = "1", monitor = "eDP-1" })
-- acer monitor screen
hl.monitor({
	output = "monitor:HDMI-A-1",
	mode = "1920x1080@60",
	position = "auto",
	scale = "1",
})
hl.workspace_rule({ workspace = "5", monitor = "HDMI-A-1" })

-- second screen will be on the right side
hl.monitor({
	output = "",
	mode = "preferred",
	position = "auto",
	scale = "auto",
})
