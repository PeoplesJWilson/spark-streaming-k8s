resource "aws_iam_instance_profile" "instance_profile" {
  name = var.iam_instance_profile_name
  role = aws_iam_role.iam_role.name
}

resource "aws_iam_role_policy" "iam_policy" {
    name = var.iam_policy_name
    role = aws_iam_role.iam_role.id

    policy = file(var.iam_policy_path)
}

resource "aws_iam_role" "iam_role" {
    name = var.iam_role_name
    assume_role_policy = file(var.iam_role_path)
}

