#!/usr/bin/env python3
"""
sign_nonce.py — 每天为 XTtools 签名防重放 nonce
采用 Gitee 文件内容 API (Content API) 写入 XTtools/nonce.txt
比 Issues 评论 API 更可靠
"""
import os, sys, json, secrets, base64, datetime, requests
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

# ===== 配置 =====
OWNER = "getime"
REPO = "huaweiroot"
FILE_PATH = "XTtools/nonce.txt"
PRIV_PATH = "./rsa_private_key.pem"
# =================

API_BASE = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/contents/{FILE_PATH}"

def main():
    # 1. 读私钥
    try:
        with open(PRIV_PATH) as f:
            key = RSA.import_key(f.read())
    except FileNotFoundError:
        print(f"[FAIL] 私钥文件未找到: {PRIV_PATH}")
        sys.exit(1)

    # 2. 生成 nonce + 日期载荷
    nonce = secrets.token_hex(16)
    today = datetime.date.today().isoformat()
    payload = f"{nonce}|{today}"

    # 3. RSA 签名
    h = SHA256.new(payload.encode())
    sig = pkcs1_15.new(key).sign(h)
    sig_b64 = base64.b64encode(sig).decode()

    # 4. 文件内容: nonce|sig_b64|date
    file_content = f"{payload}|{sig_b64}"

    # 5. 获取当前文件 SHA (更新已有文件需要)
    token = os.environ.get("GITEE_TOKEN", "")
    if not token:
        print("[FAIL] 环境变量 GITEE_TOKEN 未设置")
        sys.exit(1)

    sha = None
    r_get = requests.get(f"{API_BASE}?access_token={token}")
    if r_get.status_code == 200:
        data = r_get.json()
        if isinstance(data, dict):
            sha = data.get("sha")
            print(f"[INFO] file exists, sha={sha[:12]}... will overwrite")
        else:
            print("[INFO] path is directory, will create new file")
        
    elif r_get.status_code == 404:
        print("[INFO] 文件不存在, 将新建")

    # 6. 写入文件 (Content API)
    content_b64 = base64.b64encode(file_content.encode()).decode()
    put_data = {
        "content": content_b64,
        "message": f"chore: sign nonce for {today}",
        "branch": "master",
    }
    if sha:
        put_data["sha"] = sha

    r_put = requests.post(
        API_BASE,
        params={"access_token": token},
        json=put_data
    )

    if r_put.status_code in (201, 200):
        print(f"[OK] Nonce 已写入 XTtools/nonce.txt, 有效至 {today}")
        print(f"    nonce={nonce}")
    else:
        print(f"[FAIL] {r_put.status_code}: {r_put.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
