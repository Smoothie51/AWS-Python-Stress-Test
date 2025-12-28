This is a simple python web application about an inventory system with 2 user types: Admin & Users


Admin Credentials for application
Username: Admin
Password: Admin123


User data for EC2 AMI Creation

```
#!/bin/bash
dnf update -y
dnf install python3-pip git -y

# 2. Setup Environment
cd /home/ec2-user
export BUCKET_NAME="cloudproject22059943"
export TABLE_NAME="InventoryData"
export AWS_REGION="us-east-1"
export USERS_TABLE='Users'
export CARTS_TABLE='Carts'

# 3. Get repository 
git clone https://github.com/Smoothie51/AWS-Python-Stress-Test app_folder

# 4. Install Python Required Libraries
cd app_folder
pip3 install -r requirements.txt

# 5. Start the App
nohup python3 app.py > app.log 2>&1 &
```


User Data for Launch Template creation

```
#!/bin/bash
export BUCKET_NAME="cloudproject22059943"
export TABLE_NAME="InventoryData"
export AWS_REGION="us-east-1"
export USERS_TABLE='Users'
export CARTS_TABLE='Carts'

cd /home/ec2-user/app_folder
git pull origin main

nohup python3 app.py > app.log 2>&1 &
```

# Features

# Users
/login
- Enter their account
/register 
- register an account 

# Admin
/add 
- add a record into s3 bucket and dynamoDB
/edit
- Modify the record 
/delete
- Delete record in the dynamoDB

# User
/add
- add shop items into their carts
/update 
- changing quantity of items in carts
/remove 
- remove item from cart
