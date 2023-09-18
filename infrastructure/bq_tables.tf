resource "google_bigquery_table" "airlines_per_country" {
  dataset_id = google_bigquery_dataset.default.dataset_id
  table_id   = "airlines-per-country"

  external_data_configuration {
    autodetect    = true
    source_format = "CSV"
    source_uris = ["gs://europe-west3-composer-env-5968837e-bucket/data/airlines_per_country_gold.csv"]
  }
}

resource "google_bigquery_table" "routes_per_airline" {
  dataset_id = google_bigquery_dataset.default.dataset_id
  table_id   = "routes-per-airline"

  external_data_configuration {
    autodetect    = true
    source_format = "CSV"
    source_uris = ["gs://europe-west3-composer-env-5968837e-bucket/data/routes_per_airline_gold.csv"]
  }
}