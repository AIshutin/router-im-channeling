#!/bin/sh
gcloud functions deploy tg-bot-listener \
  --allow-unauthenticated \
  --entry-point run_tg_bot \
  --runtime python37 \
  --trigger-http
