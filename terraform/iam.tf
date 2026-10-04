resource "aws_iam_policy" "airflow_s3" {
  name = "${var.project}-airflow-s3"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [aws_s3_bucket.lake.arn, "${aws_s3_bucket.lake.arn}/*"]
    }]
  })
}

module "airflow_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${var.project}-airflow"

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["airflow:airflow-webserver", "airflow:airflow-scheduler", "airflow:airflow-triggerer"]
    }
  }

  role_policy_arns = {
    s3 = aws_iam_policy.airflow_s3.arn
  }
}
