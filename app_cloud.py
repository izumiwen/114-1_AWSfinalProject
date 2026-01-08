import os
import boto3
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --- 1. AWS 配置 (透過 IAM Role 自動授權) ---
# 不需要寫 Access Key 或 Secret Key，boto3 會自動讀取 EC2 綁定的 LabRole
S3_BUCKET = os.getenv('S3_BUCKET_NAME')
S3_REGION = os.getenv('AWS_REGION', 'us-east-1') # 教育帳號通常是 us-east-1
s3_client = boto3.client('s3', region_name=S3_REGION)

# --- 2. RDS (MySQL) 配置 ---
# 從環境變數讀取連線資訊，確保安全性
DB_USER = os.getenv('DB_USER', 'admin')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST') # 例如: your-db.xxxx.us-east-1.rds.amazonaws.com
DB_NAME = os.getenv('DB_NAME', 'lab')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 3. 資料庫模型 ---
class Asset(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    s3_key = db.Column(db.String(255), nullable=False)
    photographer = db.Column(db.String(100))
    description = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    def get_url(self):
        """產生 S3 預簽章 URL 供網頁顯示私有圖片"""
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': self.s3_key},
            ExpiresIn=3600
        )

# 初始化資料表
with app.app_context():
    db.create_all()

# --- 4. 路由邏輯 ---
@app.route('/')
def index():
    search = request.args.get('search', '')
    query = Asset.query
    if search:
        # 搜尋 RDS 中的描述或攝影師名稱
        query = query.filter(
            (Asset.description.contains(search)) | 
            (Asset.photographer.contains(search))
        )
    assets = query.order_by(Asset.upload_date.desc()).all()
    return render_template('index.html', assets=assets, search=search)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    photographer = request.form.get('photographer', 'Anonymous')
    description = request.form.get('description', '')

    if file and file.filename != '':
        # 建立 S3 Key (路徑 + 時間戳記 + 檔名)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        s3_key = f"uploads/{timestamp}_{file.filename}"
        
        try:
            # A. 上傳至 S3
            s3_client.upload_fileobj(
                file, S3_BUCKET, s3_key,
                ExtraArgs={"ContentType": file.content_type}
            )
            
            # B. 寫入 RDS
            new_asset = Asset(
                filename=file.filename,
                s3_key=s3_key,
                photographer=photographer,
                description=description
            )
            db.session.add(new_asset)
            db.session.commit()
        except Exception as e:
            print(f"Deployment Error: {e}")
            
    return redirect(url_for('index'))

if __name__ == '__main__':
    # 雲端運行必須設定 host='0.0.0.0'
    # 使用 Port 5000 (記得在 Security Group 開放)
    app.run(host='0.0.0.0', port=5000)