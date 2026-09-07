#!/usr/bin/expect
# 1. Start the su process
spawn su - minecraft

# 2. Handle the password
expect "Password:"
send "minecraft\r"

# Wait for the prompt again before sending the next command
expect -re {\[([^@]+)@([^ ]+)\s+([^\]]+)\]}
send "./backup-worlds.sh\r"

# 3. Wait for any prompt ending in $ or #, then send the commands
expect -re {\[([^@]+)@([^ ]+)\s+([^\]]+)\]}
send "cd ~/Will-World\r"

# Wait for the prompt again
expect -re {\[([^@]+)@([^ ]+)\s+([^\]]+)\]}
send "java -Xmx8048M -Xms8048M -jar paper-26.2-121.jar nogui"

# 4. Keep the session open so the server doesn't close
interact
