import os
import boto3
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

# --- AWS S3 配置 ---
# 雲端版：透過 EC2 的 IAM Role (LabRole) 自動授權
S3_BUCKET = os.getenv('S3_BUCKET_NAME')
S3_REGION = os.getenv('AWS_REGION', 'us-east-1')
s3_client = boto3.client('s3', region_name=S3_REGION)

@app.route('/')
def index():
    assets = []
    try:
        # 直接從 S3 獲取檔案清單
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix='uploads/')
        
        if 'Contents' in response:
            for obj in response['Contents']:
                # 為每個檔案產生預簽章 URL (有效期 1 小時)
                url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': obj['Key']},
                    ExpiresIn=3600
                )
                assets.append({
                    'filename': obj['Key'].split('/')[-1],
                    'url': url,
                    'last_modified': obj['LastModified'].strftime('%Y-%m-%d %H:%M')
                })
    except Exception as e:
        print(f"S3 讀取錯誤: {e}")

    # 按時間排序 (最新在上)
    assets.sort(key=lambda x: x['last_modified'], reverse=True)
    return render_template('index.html', assets=assets)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if file and file.filename != '':
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        s3_key = f"uploads/{timestamp}_{file.filename}"
        
        try:
            # 上傳檔案至 S3
            s3_client.upload_fileobj(
                file, S3_BUCKET, s3_key,
                ExtraArgs={"ContentType": file.content_type}
            )
        except Exception as e:
            print(f"S3 上傳錯誤: {e}")
            
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)