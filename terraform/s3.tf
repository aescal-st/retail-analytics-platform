data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "lake" {
  # bucket names are globally unique — account ID suffix guarantees it
  bucket        = "${var.project}-lake-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}
