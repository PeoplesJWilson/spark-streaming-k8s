locals {
    join_bucket_name="peoples-k8s-join-bucket"


    s3_full_policy_name = "s3FullAccess"
    s3_full_policy_path = "./modules/iam/s3-full-access-policy.json"
    s3_full_role_name = "ec2-s3-full-access-role"
    
    iam_role_path = "./modules/iam/ec2-assume-role-policy.json"
}