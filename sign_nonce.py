#!/usr/bin/env python3
"""
sign_nonce.py — 每天为 XTtools 签名防重放 nonce
采用 git commit + push 写入私有仓库，避免 Gitee Content API 的 404 问题
"""
import os, sys, secrets, base64, datetime, subprocess
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

# ===== 配置 =====
WORK_DIR = "./gitee_repo"
FILE_PATH = "XTtools/nonce.txt"
PRIV_PATH = "./rsa_private_key.pem"
# =================

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

    # 4. 文件内容: nonce|date|sig_b64
    file_content = f"{payload}|{sig_b64}"

    # 5. 写入文件到本地仓库
    full_path = os.path.join(WORK_DIR, FILE_PATH)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(file_content)
    print(f"[INFO] 已写入 {full_path}")

    # 6. Git commit + push
    try:
        subprocess.run(["git", "config", "user.email", "bot@xttools.dev"],
                       cwd=WORK_DIR, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "XTtools Bot"],
                       cwd=WORK_DIR, check=True, capture_output=True)
        subprocess.run(["git", "add", FILE_PATH],
                       cwd=WORK_DIR, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"chore: sign nonce for {today}"],
                       cwd=WORK_DIR, check=True, capture_output=True)
        result = subprocess.run(["git", "push"],
                                cwd=WORK_DIR, check=True, capture_output=True, text=True)
        print(f"[OK] 已推送到 Gitee (nonce={nonce})")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr
        if "nothing to commit" in stderr or "nothing to commit" in (e.stdout or ""):
            print(f"[OK] nonce 无变化, 跳过提交")
        else:
            print(f"[FAIL] git 操作失败 (code {e.returncode}): {stderr[:300]}")
            sys.exit(1)

if __name__ == "__main__":
    main()
