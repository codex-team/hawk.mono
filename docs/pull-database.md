# How to pull production database to local MongoDB instance
## Pulling events

1. Download archive (.tar.gz) with backup from codex-backup Telegram chat
2. Unarchive dump to /dump/hawk_events folder in hawk.mono directory
3. Start mongodb container: docker-compose up mongodb
4. Run ./mongorestore-events.sh

## Pulling accounts

1. Download archive (.tar.gz) with backup from codex-backup Telegram chat
2. Unarchive dump to /dump/hawk_accounts folder in hawk.mono directory
3. Start mongodb container: docker-compose up mongodb
4. Run ./mongorestore-accounts.sh