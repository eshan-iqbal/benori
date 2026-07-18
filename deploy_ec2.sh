#!/bin/bash
set -e

# Configuration
REGION="us-east-1"
KEY_NAME="fmcg-backend-key"
SG_NAME="fmcg-backend-sg"
AMI_ID="ami-04b70fa74e45c3917" # Ubuntu 24.04 LTS for us-east-1
INSTANCE_TYPE="t2.micro"
PEM_FILE="${KEY_NAME}.pem"

echo "🚀 Starting AWS Deployment in region ${REGION}..."

# 1. Create Key Pair if it doesn't exist
if [ ! -f "$PEM_FILE" ]; then
    echo "🔑 Creating Key Pair: $KEY_NAME"
    aws ec2 create-key-pair --key-name $KEY_NAME --query "KeyMaterial" --output text > $PEM_FILE
    chmod 400 $PEM_FILE
else
    echo "✅ Key Pair $PEM_FILE already exists locally."
fi

# 2. Create Security Group if it doesn't exist
SG_ID=$(aws ec2 describe-security-groups --group-names $SG_NAME --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)

if [ -z "$SG_ID" ]; then
    echo "🛡️ Creating Security Group: $SG_NAME"
    VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
    SG_ID=$(aws ec2 create-security-group --group-name $SG_NAME --description "Allow SSH and Port 8000 for FMCG Backend" --vpc-id $VPC_ID --query "GroupId" --output text)
    
    # Allow SSH (22)
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
    
    # Allow FastAPI (8000)
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0
else
    echo "✅ Security Group $SG_NAME already exists (ID: $SG_ID)."
fi

# 3. Launch EC2 Instance
echo "🖥️ Launching EC2 Instance ($INSTANCE_TYPE)..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --count 1 \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=FMCG-Backend}]' \
    --query "Instances[0].InstanceId" \
    --output text)

echo "⏳ Waiting for instance $INSTANCE_ID to enter 'running' state..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get Public IP
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].PublicIpAddress" --output text)
echo "✅ Instance is running! Public IP: $PUBLIC_IP"

# 4. Wait for SSH to be ready
echo "⏳ Waiting for SSH to become available (this takes ~60 seconds)..."
sleep 60

# 5. Package backend code
echo "📦 Packaging backend code..."
tar -czf backend.tar.gz backend/ agents/ .env requirements.txt

# 6. Upload and Setup via SSH
echo "📤 Uploading code to EC2 ($PUBLIC_IP)..."
scp -i $PEM_FILE -o StrictHostKeyChecking=no backend.tar.gz ubuntu@$PUBLIC_IP:~

echo "🛠️ Configuring server and starting FastAPI..."
ssh -i $PEM_FILE -o StrictHostKeyChecking=no ubuntu@$PUBLIC_IP << 'EOF'
    echo "Extracting code..."
    tar -xzf backend.tar.gz
    
    echo "Installing dependencies..."
    sudo apt update
    sudo apt install -y python3-pip python3-venv
    
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    echo "Starting FastAPI server in the background..."
    nohup uvicorn backend.api:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
    echo "Backend started successfully!"
EOF

echo "========================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "👉 Your API is live at: http://$PUBLIC_IP:8000/docs"
echo "Make sure to update your Next.js API_BASE_URL to point to http://$PUBLIC_IP:8000 before deploying to Vercel."
echo "========================================================="
