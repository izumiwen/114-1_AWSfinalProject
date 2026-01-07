import socket

def check_rds_port(host, port=3306):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5) # 設定 5 秒超時
    try:
        s.connect((host, port))
        return "成功連上 RDS 埠 (3306)！代表網路門禁已開。"
    except socket.timeout:
        return "連線超時 (Timeout)：可能是 Security Group 沒開 3306。"
    except ConnectionRefusedError:
        return "連線被拒絕 (Refused)：網路通了但 RDS 沒在聽（請檢查端點地址）。"
    except Exception as e:
        return f"連線失敗：{str(e)}"
    finally:
        s.close()

# 測試您的 Endpoint
print(check_rds_port("您的RDS端點字串"))