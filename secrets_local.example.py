# Template for local-only admin bootstrap credentials.
# Copy this file to `secrets_local.py` (which is git-ignored) and set your values.
# Alternatively, set the environment variables DOKU_ADMIN_USERNAME /
# DOKU_ADMIN_PASSWORD, which take precedence over this file.
#
# If neither this file nor the env vars are present, DOKU generates a random
# one-time admin password and prints it to the console on first run.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "change-me"
