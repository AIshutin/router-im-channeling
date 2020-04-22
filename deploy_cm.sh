gcloud builds submit --tag gcr.io/router-im/cm
gcloud run deploy --image gcr.io/router-im/cm --platform managed
