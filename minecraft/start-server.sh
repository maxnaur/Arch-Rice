#!/usr/bin/expect
# 1. Start the su process
spawn su - minecraft

# 2. Handle the password
expect "Password:"
send "minecraft\r"

# 3. Wait for input
expect -re {\[([^@]+)@([^ ]+)\s+([^\]]+)\]}
send "cd ~/Will-World\r"

# Wait
expect -re {\[([^@]+)@([^ ]+)\s+([^\]]+)\]}
# get ready to start the server
send "java -Xmx8048M -Xms8048M -jar paper-26.2-121.jar nogui"

# 4. Keep the session open so the server doesn't close
interact
