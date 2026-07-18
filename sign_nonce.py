#!/usr/bin/env python3
"""
sign_nonce.py — 每天为 XTtools 签名防重放 nonce
git commit + push 写入 xttools-tokens，零 HTTP API 依赖
"""
import os, sys, secrets, base64, datetime, subprocess
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

WORK_DIR = "./gitee_repo"
FILE_PATH = "XTtools/nonce.txt"
PRIV_PATH = "./rsa_private_key.pem"

def main():
    # 1. Token
    token = os.getenv("GITEE_TOKEN", "")
    if not token:
        print("[FAIL] GITEE_TOKEN 未设置")
        sys.exit(1)
    print(f"[INFO] token 长度={len(token)}")

    # 2. 私钥
    try:
        with open(PRIV_PATH) as f:
            key = RSA.import_key(f.read())
    except FileNotFoundError:
        print(f"[FAIL] {PRIV_PATH} 未找到")
        sys.exit(1)

    # 3. 生成 nonce + 签名
    nonce = secrets.token_hex(16)
    today = datetime.date.today().isoformat()
    payload = f"{nonce}|{today}"
    h = SHA256.new(payload.encode())
    sig = pkcs1_15.new(key).sign(h)
    sig_b64 = base64.b64encode(sig).decode()
    content = f"{payload}|{sig_b64}"

    # 4. 写入文件
    full_path = os.path.join(WORK_DIR, FILE_PATH)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    print(f"[INFO] 已写入 {full_path}")

    # 5. Git commit + push
    cmds = [
        (["git", "config", "user.email", "bot@xttools.dev"], False),
        (["git", "config", "user.name", "XTtools Bot"], False),
        (["git", "add", FILE_PATH], False),
        (["git", "commit", "-m", f"chore: sign nonce for {today}"], False),
        (["git", "push"], True),
    ]
    for cmd, is_push in cmds:
        r = subprocess.run(cmd, cwd=WORK_DIR, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        if r.returncode != 0:
            if "nothing to commit" in out:
                print("[INFO] 无变化，跳过")
                sys.exit(0)
            if is_push:
                print(f"[FAIL] git push 失败 (code {r.returncode})")
                print(f"  stderr: {r.stderr[:300]}")
                print(f"  stdout: {r.stdout[:200]}")
                sys.exit(1)
            else:
                print(f"[WARN] {cmd[1]} 非致命: {out[:100]}")
        else:
            if cmd[0] == "git push":
                print(f"[OK] 已推送到 Gitee (nonce={nonce})")
    print("[OK] 完成")

if __name__ == "__main__":
    main()
