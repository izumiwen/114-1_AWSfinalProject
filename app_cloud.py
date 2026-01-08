import os
import boto3
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

S3_BUCKET = os.getenv('S3_BUCKET_NAME')
S3_REGION = os.getenv('AWS_REGION')
s3_client = boto3.client('s3', region_name=S3_REGION)

@app.route('/')
def index():
    assets = []
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix='uploads/')
        
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['Key'] == 'uploads/': continue
                
                # 獲取個別物件的詳細資訊（包含 Metadata）
                head = s3_client.head_object(Bucket=S3_BUCKET, Key=obj['Key'])
                metadata = head.get('Metadata', {})

                # 解碼中文內容
                photographer = urllib.parse.unquote(metadata.get('photographer', 'Anonymous'))
                description = urllib.parse.unquote(metadata.get('description', ''))

                url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': obj['Key']},
                    ExpiresIn=3600
                )
                
                assets.append({
                    'filename': obj['Key'].split('/')[-1],
                    'url': url,
                    'photographer': photographer,
                    'description': description,
                    'upload_date': obj['LastModified']
                })
        
        assets.sort(key=lambda x: x['upload_date'], reverse=True)
            
    except Exception as e:
        print(f"S3 讀取錯誤: {e}")

    return render_template('index.html', assets=assets)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    # 接收表單資訊
    photographer = request.form.get('photographer', 'Anonymous')
    description = request.form.get('description', '')

    if file and file.filename != '':
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        s3_key = f"uploads/{timestamp}_{file.filename}"
        
        # 對中文進行編碼以符合 S3 HTTP Header 規範
        safe_photographer = urllib.parse.quote(photographer)
        safe_description = urllib.parse.quote(description)

        try:
            # 將資料放入 Metadata 中隨檔案上傳
            s3_client.upload_fileobj(
                file, S3_BUCKET, s3_key,
                ExtraArgs={
                    "ContentType": file.content_type,
                    "Metadata": {
                        "photographer": safe_photographer,
                        "description": safe_description
                    }
                }
            )
        except Exception as e:
            print(f"S3 上傳錯誤: {e}")
            
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)