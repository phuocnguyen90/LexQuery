# cdk/embedding_service_stack.py

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct

class EmbeddingServiceStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(self, "EmbeddingServiceVPC",
                      max_azs=2,
                      nat_gateways=1)

        # Define a Security Group
        security_group = ec2.SecurityGroup(self, "EmbeddingServiceSG",
                                           vpc=vpc,
                                           description="Allow HTTP traffic on port 8000",
                                           allow_all_outbound=True)
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(),
                                        ec2.Port.tcp(8000),
                                        "Allow inbound HTTP traffic on port 8000")

        # IAM Role for EC2 Instance
        ec2_role = iam.Role(self, "EmbeddingServiceRole",
                            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                            description="Role for Embedding Service EC2 Instance")
        ec2_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))

        # User Data Script to Set Up the EC2 Instance
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "#!/bin/bash",
            "sudo yum update -y",
            "sudo yum install -y python3 git",
            "curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3",
            "git clone https://github.com/phuocnguyen90/legal_qa_rag.git /home/ec2-user/embedding_service",
            "cd /home/ec2-user/embedding_service",
            "python3 -m venv venv",
            "source venv/bin/activate",
            "pip install --upgrade pip",
            "pip install -r app/requirements.txt",
            # Pre-download the model to reduce startup time
            "python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')\"",
            # Create systemd service for the FastAPI application
            "echo '[Unit]' | sudo tee /etc/systemd/system/embedding.service",
            "echo 'Description=Embedding Service' | sudo tee -a /etc/systemd/system/embedding.service",
            "echo 'After=network.target' | sudo tee -a /etc/systemd/system/embedding.service",
            "",
            "echo '[Service]' | sudo tee -a /etc/systemd/system/embedding.service",
            "echo 'User=ec2-user' | sudo tee -a /etc/systemd/system/embedding.service",
            "echo 'WorkingDirectory=/home/ec2-user/embedding_service' | sudo tee -a /etc/systemd/system/embedding.service",
            "echo 'ExecStart=/home/ec2-user/embedding_service/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000' | sudo tee -a /etc/systemd/system/embedding.service",
            "echo 'Restart=always' | sudo tee -a /etc/systemd/system/embedding.service",
            "",
            "echo '[Install]' | sudo tee -a /etc/systemd/system/embedding.service",
            "echo 'WantedBy=multi-user.target' | sudo tee -a /etc/systemd/system/embedding.service",
            "",
            "sudo systemctl daemon-reload",
            "sudo systemctl enable embedding.service",
            "sudo systemctl start embedding.service"
        )

        # Define the EC2 Instance
        instance = ec2.Instance(self, "EmbeddingServiceInstance",
                                instance_type=ec2.InstanceType("t2.small"),
                                machine_image=ec2.AmazonLinuxImage(
                                    generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
                                ),
                                vpc=vpc,
                                security_group=security_group,
                                role=ec2_role,
                                user_data=user_data)

        # Output the Public DNS of the EC2 Instance
        CfnOutput(self, "InstancePublicDNS",
                  value=instance.instance_public_dns_name,
                  description="Public DNS of the Embedding Service EC2 Instance")
