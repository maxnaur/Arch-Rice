-------------------
---- AUTOSTART ----
-------------------

-- See https://wiki.hypr.land/Configuring/Basics/Autostart/

-- Autostart necessary processes (like notifications daemons, status bars, etc.)
-- Or execute your favorite apps at launch like this:

hl.on("hyprland.start", function()
	--hl.exec_cmd(terminal)
	hl.exec_cmd("hyprctl setcursor breeze_cursors 24")
	hl.exec_cmd("brightnessctl -qd intel_backlight set 70%")
	hl.exec_cmd("systemctl --user start hyprpolkitagent")
	hl.exec_cmd("nm-applet & dunst")
	hl.exec_cmd("waybar & hyprpaper")
end)
