resource "random_password" "redshift" {
  length      = 16
  special     = false
  min_upper   = 1
  min_lower   = 1
  min_numeric = 1
}


resource "aws_iam_role" "redshift_s3" {
  name = "${var.project}-redshift-s3"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "redshift.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "redshift_s3" {
  name = "${var.project}-redshift-s3-policy"
  role = aws_iam_role.redshift_s3.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = [aws_s3_bucket.lake.arn, "${aws_s3_bucket.lake.arn}/*"]
    }]
  })
}

resource "aws_redshiftserverless_namespace" "main" {
  namespace_name      = "${var.project}-ns"
  db_name             = "retail"
  admin_username      = "admin"
  admin_user_password = random_password.redshift.result
  iam_roles           = [aws_iam_role.redshift_s3.arn]
}

resource "aws_redshiftserverless_workgroup" "main" {
  workgroup_name      = "${var.project}-wg"
  namespace_name      = aws_redshiftserverless_namespace.main.namespace_name
  base_capacity       = 8
  subnet_ids          = module.vpc.public_subnets
  security_group_ids  = [aws_security_group.redshift.id]
  publicly_accessible = true
}

resource "aws_security_group" "redshift" {
  name   = "${var.project}-redshift-sg"
  vpc_id = module.vpc.vpc_id
  ingress {
    from_port   = 5439
    to_port     = 5439
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # sandbox only — never this open in prod
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
