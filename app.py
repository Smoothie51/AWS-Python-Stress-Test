# app.py
from flask import Flask, request, render_template, redirect, url_for, session
from functools import wraps
import boto3
import uuid
import time
import math
import threading
import os

app = Flask(__name__)
app.secret_key = 'simple-secret-key'

# CONFIG 
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'cloudproject22059943')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
TABLE_NAME = os.environ.get('TABLE_NAME', 'InventoryData')
USERS_TABLE = os.environ.get('USERS_TABLE', 'Users')
CARTS_TABLE = os.environ.get('CARTS_TABLE', 'Carts')

# AWS clients
s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
inventory_table = dynamodb.Table(TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE)
carts_table = dynamodb.Table(CARTS_TABLE)

# Decorator for admin routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator for logged-in users
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_panel'))
        return redirect(url_for('shop'))
    return redirect(url_for('login'))

# ============ AUTHENTICATION ============

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user exists
        try:
            response = users_table.get_item(Key={'Username': username})
            if 'Item' in response:
                return render_template('register.html', error='Username already exists')
        except:
            pass
        
        # Create user
        user_id = str(uuid.uuid4())
        users_table.put_item(Item={
            'Username': username,
            'UserID': user_id,
            'Password': password,
            'IsAdmin': False
        })
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            response = users_table.get_item(Key={'Username': username})
            if 'Item' in response:
                user = response['Item']
                if user['Password'] == password:
                    session['user_id'] = user['UserID']
                    session['username'] = username
                    session['is_admin'] = user.get('IsAdmin', False)
                    
                    if session['is_admin']:
                        return redirect(url_for('admin_panel'))
                    else:
                        return redirect(url_for('shop'))
        except:
            pass
        
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============ SHOP (USER) ============

@app.route('/shop')
@login_required
def shop():
    response = inventory_table.scan()
    items = response.get('Items', [])
    
    for item in items:
        try:
            item['ImageURL'] = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': item['ItemID']},
                ExpiresIn=3600
            )
        except:
            item['ImageURL'] = ''
    
    return render_template('shop.html', items=items)

@app.route('/cart/add/<item_id>', methods=['POST'])
@login_required
def add_to_cart(item_id):
    user_id = session['user_id']
    cart_key = f"{user_id}#{item_id}"
    
    try:
        item_response = inventory_table.get_item(Key={'ItemID': item_id})
        if 'Item' not in item_response:
            return redirect(url_for('shop'))
        
        item = item_response['Item']
        quantity = int(request.form.get('quantity', 1))
        
        # Check if already in cart
        try:
            cart_response = carts_table.get_item(Key={'CartKey': cart_key})
            if 'Item' in cart_response:
                current_qty = int(cart_response['Item']['Quantity'])
                new_qty = current_qty + quantity
                carts_table.update_item(
                    Key={'CartKey': cart_key},
                    UpdateExpression='SET Quantity = :qty',
                    ExpressionAttributeValues={':qty': new_qty}
                )
            else:
                carts_table.put_item(Item={
                    'CartKey': cart_key,
                    'UserID': user_id,
                    'ItemID': item_id,
                    'ItemName': item['Name'],
                    'Price': item['Price'],
                    'Quantity': quantity
                })
        except:
            carts_table.put_item(Item={
                'CartKey': cart_key,
                'UserID': user_id,
                'ItemID': item_id,
                'ItemName': item['Name'],
                'Price': item['Price'],
                'Quantity': quantity
            })
    except:
        pass
    
    return redirect(url_for('shop'))

@app.route('/cart')
@login_required
def view_cart():
    user_id = session['user_id']
    
    try:
        from boto3.dynamodb.conditions import Attr
        response = carts_table.scan(
            FilterExpression=Attr('UserID').eq(user_id)
        )
        cart_items = response.get('Items', [])
    except Exception as e:
        print(f"Cart scan error: {e}")
        cart_items = []
    
    total = 0
    
    for item in cart_items:
        try:
            item['ImageURL'] = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': item['ItemID']},
                ExpiresIn=3600
            )
        except:
            item['ImageURL'] = ''
        
        try:
            item_total = float(item['Price']) * int(item['Quantity'])
            item['ItemTotal'] = f"{item_total:.2f}"
            total += item_total
        except:
            item['ItemTotal'] = "0.00"
    
    return render_template('cart.html', cart_items=cart_items, total=f"{total:.2f}")

@app.route('/cart/remove/<item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    user_id = session['user_id']
    cart_key = f"{user_id}#{item_id}"
    
    try:
        carts_table.delete_item(Key={'CartKey': cart_key})
    except:
        pass
    
    return redirect(url_for('view_cart'))

@app.route('/cart/update/<item_id>', methods=['POST'])
@login_required
def update_cart_quantity(item_id):
    user_id = session['user_id']
    cart_key = f"{user_id}#{item_id}"
    quantity = int(request.form.get('quantity', 1))
    
    if quantity <= 0:
        return remove_from_cart(item_id)
    
    try:
        carts_table.update_item(
            Key={'CartKey': cart_key},
            UpdateExpression='SET Quantity = :qty',
            ExpressionAttributeValues={':qty': quantity}
        )
    except:
        pass
    
    return redirect(url_for('view_cart'))

# ============ ADMIN ============

@app.route('/admin')
@admin_required
def admin_panel():
    response = inventory_table.scan()
    items = response.get('Items', [])
    
    for item in items:
        try:
            item['ImageURL'] = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': item['ItemID']},
                ExpiresIn=3600
            )
        except:
            pass
    
    return render_template('admin.html', items=items)

@app.route('/admin/add', methods=['POST'])
@admin_required
def admin_add_item():
    item_id = str(uuid.uuid4())
    s3.upload_fileobj(request.files['image'], BUCKET_NAME, item_id)
    
    inventory_table.put_item(Item={
        'ItemID': item_id,
        'Name': request.form['name'],
        'Price': request.form['price']
    })
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/edit/<item_id>')
@admin_required
def admin_edit_item(item_id):
    response = inventory_table.get_item(Key={'ItemID': item_id})
    item = response.get('Item')
    
    if not item:
        return redirect(url_for('admin_panel'))
    
    try:
        item['ImageURL'] = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': item['ItemID']},
            ExpiresIn=3600
        )
    except:
        item['ImageURL'] = ''
    
    return render_template('edit.html', item=item)

@app.route('/admin/update/<item_id>', methods=['POST'])
@admin_required
def admin_update_item(item_id):
    inventory_table.update_item(
        Key={'ItemID': item_id},
        UpdateExpression='SET #name = :name, Price = :price',
        ExpressionAttributeNames={'#name': 'Name'},
        ExpressionAttributeValues={
            ':name': request.form['name'],
            ':price': request.form['price']
        }
    )
    
    if 'image' in request.files and request.files['image'].filename:
        s3.upload_fileobj(request.files['image'], BUCKET_NAME, item_id)
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/<item_id>', methods=['POST'])
@admin_required
def admin_delete_item(item_id):
    s3.delete_object(Bucket=BUCKET_NAME, Key=item_id)
    inventory_table.delete_item(Key={'ItemID': item_id})
    return redirect(url_for('admin_panel'))

# ============ HEALTH & STRESS ============

@app.route('/health')
def health():
    return "Healthy", 200

def burn_cpu():
    t_end = time.time() + 60 * 2
    while time.time() < t_end:
        math.sqrt(64*64*64*64)

@app.route('/stress')
@admin_required
def stress():
    thread = threading.Thread(target=burn_cpu)
    thread.start()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)