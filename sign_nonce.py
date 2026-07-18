#!/usr/bin/env python3
"""
sign_nonce.py — 每天为 XTtools 签名防重放 nonce
用法: python sign_nonce.py
需要环境变量 GITEE_TOKEN (PAT, 需 issues:write 权限)
或直接编辑下方配置
"""
import os, sys, json, secrets, base64, datetime, requests
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

# ===== 配置（可改）=====
OWNER = "getime"
REPO = "huaweiroot"
ISSUE_NUM = 1          # 新建 Issue 后确认编号
PRIV_PATH = "./rsa_private_key.pem"   # 私钥路径
# ========================

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

    # 4. 评论内容
    comment_body = f"{nonce}|{sig_b64}"

    # 5. 发到 Gitee Issue
    token = os.environ.get("GITEE_TOKEN", "")
    if not token:
        print("[FAIL] 环境变量 GITEE_TOKEN 未设置")
        sys.exit(1)

    url = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/issues/{ISSUE_NUM}/comments"
    resp = requests.post(url, json={"body": comment_body},
                         params={"access_token": token})

    if resp.status_code == 201:
        print(f"[OK] Nonce 已发布 (Issue #{ISSUE_NUM}), 有效至 {today}")
        print(f"    nonce={nonce} sig_len={len(sig_b64)}")
    elif resp.status_code == 401:
        print(f"[FAIL] PAT 权限不足，需要 'notes' scope")
        print(f"    → 去 Gitee 设置 → 个人访问令牌 → 编辑 → 勾选 'notes'（评论）")
        sys.exit(1)
    else:
        print(f"[FAIL] {resp.status_code}: {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
