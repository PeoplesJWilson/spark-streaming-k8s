locals {
    twelve_data_key = "notmykey"
    symbols = ["AAPL","MSFT"]
    spark = ["0","1"]
    n_samples = 10

    master_nodes = ["1"]
    worker_nodes = ["1","2","3","4","5","6","7","8"]

    join_bucket_name="peoples-k8s-join-bucket"

    postgres_username = "postgres"
    postgres_password = "123notmypassword456dontworry"
    postgres_db_name = "postgres_airflow"
    airflow_username = "airflow"
    airflow_password = "123notmypassword456dontworry"


    s3_full_policy_name = "s3FullAccess"
    s3_full_policy_path = "./modules/iam/s3-full-access-policy.json"
    s3_full_role_name = "ec2-s3-full-access-role"
    
    iam_role_path = "./modules/iam/ec2-assume-role-policy.json"
}


locals {
    symbol_strings = [
        for idx, symbol in local.symbols :
            "  - name: TOPIC_${idx}\n    value: ${symbol}"
    ]
}
locals {
    yaml_symbol_string = join("\n", local.symbol_strings)
}