#!/usr/bin/expect
# 1. Start the su process
spawn su - minecraft

# 2. Handle the password
expect "Password:"
send "minecraft\r"

# 3. Keep the session open so the server doesn't close
interact
