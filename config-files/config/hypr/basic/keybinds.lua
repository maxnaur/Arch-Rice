---------------------
---- MY PROGRAMS ----
---------------------

local terminal = "kitty"
local fileManager = "dolphin"
local menu = "rofi -show drun"
local appswap = "rofi -show window"
local screenshot = "flameshot gui"
local internet1 = "zen-browser"
local internet2 = "helium-browser"
local internet3 = "firefox"
local discord = "bash -lc '__NV_PRIME_RENDER_OFFLOAD=0 __GLX_VENDOR_LIBRARY_NAME=mesa DRI_PRIME=0 vesktop'"
local bluetooth = "blueberry"
local steam = "steam"
local minecraft = "prismlauncher"

---------------------
---- KEYBINDINGS ----
---------------------

local mainMod = "SUPER" -- use "Windows" key as main modifier

-- basic
local closeWindowBind = hl.bind(mainMod .. " + C", hl.dsp.window.close())
closeWindowBind:set_enabled(true)

hl.bind(mainMod .. " + N", hl.dsp.exec_cmd("hyprlock")) -- lock
hl.bind(
	mainMod .. " + M",
	hl.dsp.exec_cmd("command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'")
) -- logout

-- launch apps
hl.bind(mainMod .. " + Q", hl.dsp.exec_cmd(terminal))
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd(fileManager))
hl.bind("ALT + space", hl.dsp.exec_cmd(menu))
hl.bind("ALT + tab", hl.dsp.exec_cmd(appswap))
hl.bind("SUPER + SHIFT + S", hl.dsp.exec_cmd(screenshot))
hl.bind(mainMod .. " + R", hl.dsp.exec_cmd(discord))
hl.bind(mainMod .. " + T", hl.dsp.exec_cmd(bluetooth))

hl.bind(mainMod .. " + Y", hl.dsp.exec_cmd(minecraft))
hl.bind(mainMod .. " + U", hl.dsp.exec_cmd(steam))

hl.bind(mainMod .. " + A", hl.dsp.exec_cmd(internet1))
hl.bind(mainMod .. " + S", hl.dsp.exec_cmd(internet2))
hl.bind(mainMod .. " + D", hl.dsp.exec_cmd(internet3))

-- manage windows
hl.bind(mainMod .. " + V", hl.dsp.window.float({ action = "toggle" }))
hl.bind(mainMod .. " + P", hl.dsp.window.pseudo())
hl.bind(mainMod .. " + G", hl.dsp.layout("togglesplit")) -- dwindle only

-- Move focus with mainMod + arrow keys
hl.bind(mainMod .. " + left", hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + up", hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + down", hl.dsp.focus({ direction = "down" }))
-- vim movement
hl.bind(mainMod .. " + H", hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + J", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + K", hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + L", hl.dsp.focus({ direction = "down" }))

-- Switch workspaces with mainMod + [0-9]
-- Move active window to a workspace with mainMod + SHIFT + [0-9]
for i = 1, 10 do
	local key = i % 10 -- 10 maps to key 0
	hl.bind(mainMod .. " + " .. key, hl.dsp.focus({ workspace = i }))
	hl.bind(mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end

-- Laptop shut lid
-- Trigger on any lid toggle to lock the screen
hl.bind("switch:Lid Switch", hl.dsp.exec_cmd("hyprlock"))

-- Example special workspace (scratchpad)
--hl.bind(mainMod .. " + S", hl.dsp.workspace.toggle_special("magic"))
--hl.bind(mainMod .. " + SHIFT + S", hl.dsp.window.move({ workspace = "special:magic" }))

-- Scroll through existing workspaces with mainMod + scroll
--hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
--hl.bind(mainMod .. " + mouse_up", hl.dsp.focus({ workspace = "e-1" }))

-- Move/resize windows with mainMod + LMB/RMB and dragging
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Laptop multimedia keys for volume and LCD brightness
hl.bind(
	"XF86AudioRaiseVolume",
	hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"),
	{ locked = true, repeating = true }
)
hl.bind(
	"XF86AudioLowerVolume",
	hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),
	{ locked = true, repeating = true }
)
hl.bind(
	"XF86AudioMute",
	hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),
	{ locked = true, repeating = true }
)
hl.bind(
	"XF86AudioMicMute",
	hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"),
	{ locked = true, repeating = true }
)
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%-"), { locked = true, repeating = true })

-- Requires playerctl
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })
