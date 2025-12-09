from flask import Flask, request
import boto3
import uuid
import time
import math

app = Flask(__name__)

# CONFIG - CHANGE THIS BUCKET NAME!
BUCKET_NAME = 'cloudproject22059943'
REGION = 'us-east-1'

# Auto-connects using the LabRole (No keys needed)
s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table('InventoryData')

@app.route('/')
def home():
    return """
    <h1>Cloud Inventory System</h1>
    <form action="/add" method="post" enctype="multipart/form-data">
        <input type="text" name="name" placeholder="Item Name" required><br>
        <input type="text" name="price" placeholder="Price" required><br>
        <input type="file" name="image" required><br>
        <button type="submit">Upload Item</button>
    </form>
    <br>
    <a href="/stress"><button style="background-color:red; color:white;">⚠️ TRIGGER CPU STRESS TEST</button></a>
    """

@app.route('/health')
def health():
    return "Healthy", 200

@app.route('/add', methods=['POST'])
def add_item():
    item_id = str(uuid.uuid4())
    # 1. Upload to S3
    s3.upload_fileobj(request.files['image'], BUCKET_NAME, item_id)
    # 2. Write to DB
    table.put_item(Item={
        'ItemID': item_id,
        'Name': request.form['name'],
        'Price': request.form['price']
    })
    return "Item Saved! <a href='/'>Go Back</a>"

@app.route('/stress')
def stress():
    # BURNS CPU FOR 60 SECONDS to trigger Auto Scaling
    timeout = time.time() + 60
    while time.time() < timeout:
        math.sqrt(64*64*64*64) 
    return "Stress Test Complete! Check CloudWatch."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)