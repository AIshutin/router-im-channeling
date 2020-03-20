For local testing use:
`uvicorn channel_manager:app --port 2000 --host 0.0.0.0 --reload`
`python3 server_test.py --live -1 --channel tg_bot --type text`
`functions-framework --target run_$channel --port 80 --host 0.0.0.0`
