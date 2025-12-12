# app.py
from flask import Flask, request, render_template, redirect, url_for
import boto3
import uuid

app = Flask(__name__)

# CONFIG - CHANGE THIS BUCKET NAME!
BUCKET_NAME = 'cloudproject22059943'
REGION = 'us-east-1'

# Auto-connects using the LabRole (No keys needed)
s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table('InventoryData')

@app.route('/admin')
def admin_panel():
    # Fetch all items from DynamoDB
    response = table.scan()
    items = response.get('Items', [])
    
    for item in items:
        try:
            secure_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': item['ItemID']},
                ExpiresIn=3600  # Link valid for 1 hour
            )
            item['ImageURL'] = secure_url
        except Exception as e:
            print(f"Error signing link for {item['ItemID']}: {e}")

    message = request.args.get('message')
    
    return render_template('admin.html', 
                         items=items, 
                         bucket=BUCKET_NAME, 
                         region=REGION,
                         message=message)


@app.route('/admin/add', methods=['POST'])
def admin_add_item():
    item_id = str(uuid.uuid4())
    
    # Upload to S3
    s3.upload_fileobj(request.files['image'], BUCKET_NAME, item_id)
    
    # Write to DynamoDB
    table.put_item(Item={
        'ItemID': item_id,
        'Name': request.form['name'],
        'Price': request.form['price']
    })
    
    return redirect(url_for('admin_panel', message='Item added successfully!'))

@app.route('/admin/edit/<item_id>')
def admin_edit_item(item_id):
    # Get item from DynamoDB
    response = table.get_item(Key={'ItemID': item_id})
    item = response.get('Item')
    
    if not item:
        return redirect(url_for('admin_panel', message='Item not found!'))
    
    return render_template('edit.html', 
                         item=item, 
                         bucket=BUCKET_NAME, 
                         region=REGION)

@app.route('/admin/update/<item_id>', methods=['POST'])
def admin_update_item(item_id):
    # Update item in DynamoDB
    table.update_item(
        Key={'ItemID': item_id},
        UpdateExpression='SET #name = :name, Price = :price',
        ExpressionAttributeNames={'#name': 'Name'},
        ExpressionAttributeValues={
            ':name': request.form['name'],
            ':price': request.form['price']
        }
    )
    
    # If new image is uploaded, replace in S3
    if 'image' in request.files and request.files['image'].filename:
        s3.upload_fileobj(request.files['image'], BUCKET_NAME, item_id)
    
    return redirect(url_for('admin_panel', message='Item updated successfully!'))

@app.route('/admin/delete/<item_id>', methods=['POST'])
def admin_delete_item(item_id):
    # Delete from S3
    s3.delete_object(Bucket=BUCKET_NAME, Key=item_id)
    
    # Delete from DynamoDB
    table.delete_item(Key={'ItemID': item_id})
    
    return redirect(url_for('admin_panel', message='Item deleted successfully!'))

@app.route('/health')
def health():
    return "Healthy", 200

@app.route('/stress')
def stress():
    import time
    import math
    # BURNS CPU FOR 60 SECONDS to trigger Auto Scaling
    timeout = time.time() + 60
    while time.time() < timeout:
        math.sqrt(64*64*64*64) 
    return "Stress Test Complete! Check CloudWatch."


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)