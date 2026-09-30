-- Extra autostart processes.
-- o.launch_on_start("my-service")

-- Open Keeper using the existing Edge profile after desktop login.
o.launch_on_start("@@HOME@@/.local/bin/keeper-app")

-- taskgrid: start the task overlay at login.
o.launch_on_start("@@HOME@@/.local/bin/taskgrid")
