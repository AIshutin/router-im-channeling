## Usage:

For local testing use:

`uvicorn channel_manager:app --port 2000 --host 0.0.0.0 --reload --log-level debug`

`python3 server_interactor.py --live -1 --channel tg_bot --type text`

`functions-framework --target run_$channel --port 80 --host 0.0.0.0`

pytest usage example:

`pytest test/fb_test.py -k forward -o log_cli=true -o log_cli_level=debug`

## Environmental variables:

### All:
`$MONGO_LINK` - authentication link to access `MongoDB`

### Channel manager
None
### Webhook listeners, e. g. vk_listener for vk
None
### Platform servers, e. g. email_server for email
`$POLLING_TIME` - the approximate time N +- 2 seconds after which it's garanteed that `timestamp` in channel record in `MongoDB` will be updated by the server. If it's not updated, then there is no server which handles this channel.
`$API_ID` - API_ID in Telegram. (Only for `tg_server`)
`$API_HASH` - API_HASH in Telegram. (Only for `tg_server`)

## Upserting telegram user account
To upsert account you need to provide I. link or II. base64 `pyrogram` .session file.
I. Link case
In 60 seconds the `POST` request will be sent to this link. The response must contain JSON with `code` field with telegram access code.
II. base64 `pyrogram` .session file
It's not recommended way.

## Notes
Enable IMAP and POP3 for email account.
On Facebook, the response to user must be sent in 24h window. Otherwise, it will not be sent.
You must increase timeout for email and tg channels upsertion.
