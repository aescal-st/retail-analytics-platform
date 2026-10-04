output "bucket_name" {
  value = aws_s3_bucket.lake.bucket
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "redshift_endpoint" {
  value = aws_redshiftserverless_workgroup.main.endpoint[0].address
}

output "redshift_password" {
  value     = random_password.redshift.result
  sensitive = true
}

output "airflow_irsa_role_arn" {
  value = module.airflow_irsa.iam_role_arn
}
