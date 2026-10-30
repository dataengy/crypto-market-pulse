# Opt-in cloud deployment: Pub/Sub -> native BigQuery Subscription (raw BYTES).
# Run `terraform plan` manually; costs apply if resources are applied.
terraform {
  required_version = ">= 1.5"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
}
variable "project_id" { type = string }
variable "region" { type = string, default = "europe-west1" }
provider "google" { project = var.project_id, region = var.region }
data "google_project" "current" { project_id = var.project_id }
resource "google_project_service" "pubsub" { service = "pubsub.googleapis.com" disable_on_destroy = false }
resource "google_project_service" "bigquery" { service = "bigquery.googleapis.com" disable_on_destroy = false }
resource "google_pubsub_topic" "trades" {
  name = "market-trades-v1"
  depends_on = [google_project_service.pubsub]
}
resource "google_bigquery_dataset" "market" {
  dataset_id = "crypto_pulse"
  location = "EU"
  depends_on = [google_project_service.bigquery]
}
resource "google_bigquery_table" "raw" {
  dataset_id = google_bigquery_dataset.market.dataset_id
  table_id = "trades_raw"
  deletion_protection = true
  schema = jsonencode([
    { name = "data", type = "BYTES", mode = "NULLABLE" }
  ])
}
resource "google_bigquery_dataset_iam_member" "pubsub_write" {
  dataset_id = google_bigquery_dataset.market.dataset_id
  role = "roles/bigquery.dataEditor"
  member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
resource "google_pubsub_subscription" "to_bigquery" {
  name = "market-trades-to-bigquery"
  topic = google_pubsub_topic.trades.id
  bigquery_config {
    table = "${var.project_id}.${google_bigquery_dataset.market.dataset_id}.${google_bigquery_table.raw.table_id}"
    use_topic_schema = false
    use_table_schema = false
    write_metadata = false
  }
  depends_on = [google_bigquery_dataset_iam_member.pubsub_write]
}
output "topic_id" { value = google_pubsub_topic.trades.id }
output "table_id" { value = google_bigquery_table.raw.id }
