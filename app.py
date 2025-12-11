import os
import boto3
import uuid
import time
import math
from flask import Flask, request, render_template, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# --- CONFIGURATION ---
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'cloudproject22059943')
TABLE_NAME = os.environ.get('TABLE_NAME', 'InventoryData')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

@app.route('/')
def home():
    try:
        response = table.scan()
        items = response.get('Items', [])
        # CHANGE: Now loading a file instead of a string
        return render_template('index.html', items=items) 
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return render_template('index.html', items=[])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)