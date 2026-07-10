# Tencent Cloud Infrastructure Setup

## One-time setup (performed once by admin via Tencent Cloud console)

### 1. Create VPC
- Name: examlab-vpc
- CIDR: 10.0.0.0/16

### 2. Create Subnets
- Public subnet: 10.0.1.0/24 (for management server)
- Private subnet: 10.0.2.0/23 (for exam VMs, ~512 IPs)

### 3. Create NAT Gateway
- Bind to public subnet
- Associate with private subnet's route table
- Enables exam VMs to access internet (yum/apt)

### 4. Create Management Security Group (sg-mgmt)
- Ingress: SSH 22 from your IP, HTTPS 443 from 0.0.0.0/0
- Egress: All

### 5. Launch Management CVM
- Spec: 4 CPU, 8GB RAM, 100GB SSD
- OS: CentOS 7.9 or Ubuntu 22.04
- Place in public subnet, bind management security group
- Allocate and bind an EIP (BGP)

### 6. Create API Access Key
- CAM console -> API Keys -> Create
- Copy SecretId and SecretKey to .env file

### 7. Prepare VM Images

#### Windows Management Machine Image
1. Launch a base Windows Server 2019/2022 CVM
2. Install OpenSSH Client (for SSH to Linux)
3. Install Chrome or Firefox browser
4. Copy exam bat scripts to `C:\ExamScripts\`
5. Optionally install VS Code, Notepad++
6. Configure Windows Firewall to allow RDP (3389)
7. Enable Remote Desktop
8. Run Sysprep and create custom image
9. Note the resulting image ID

#### Linux Target Server Image
1. Launch a base CentOS 7/8 or Ubuntu 20.04 CVM
2. Install openssh-server
3. Pre-install exam software (Nginx, MySQL, Docker, etc.)
4. Create exam user account with initial password
5. Configure sudo permissions
6. Open SSH port 22
7. Create custom image
8. Note the resulting image ID

### 8. Deploy Application

```bash
# On management server
git clone <repository-url> /opt/examlab
cd /opt/examlab
cp .env.example .env
# Edit .env with actual values (Tencent Cloud keys, VPC IDs, image IDs)
nano .env

# Start all services
docker compose up -d --build

# Create admin superuser
docker compose exec backend python manage.py createsuperuser

# Verify
curl http://localhost/admin/
```

### 9. Post-Deployment Steps

1. Access admin panel at `http://<EIP>/admin/`
2. Import student accounts via CSV
3. Create exam images via Tencent Cloud console
4. Create first exam with VM spec JSON configuration
5. Assign students to exam VmGroups
6. Mark exam as "Ready" and create VMs
