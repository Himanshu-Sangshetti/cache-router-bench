#!/bin/bash
# Launch the demo box (m7i.4xlarge · ~$0.81/hr · fits default 16-vCPU quota)
set -e; cd "$(dirname "$0")"; source ./lib.sh
aws ec2 describe-security-groups --group-names llmd-demo >/dev/null 2>&1 || {
  aws ec2 create-security-group --group-name llmd-demo --description "llm-d demo" >/dev/null
  aws ec2 authorize-security-group-ingress --group-name llmd-demo \
    --protocol tcp --port 22 --cidr "$(curl -s ifconfig.me)/32" >/dev/null; }
[ -f "$KEY" ] || { aws ec2 create-key-pair --key-name llmd-demo \
    --query KeyMaterial --output text > "$KEY" && chmod 400 "$KEY"; }
AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)
ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type m7i.4xlarge \
  --key-name llmd-demo --security-groups llmd-demo \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":200,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=llmd-demo}]' \
  --query 'Instances[0].InstanceId' --output text)
save INSTANCE_ID "$ID"
echo "instance $ID launching..."
aws ec2 wait instance-running --instance-ids "$ID"
IP=$(aws ec2 describe-instances --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
save IP "$IP"
echo "box up: $IP  (ssh in ~30s)  ->  next: HF_TOKEN=hf_xxx ./1_bootstrap_stack.sh"
