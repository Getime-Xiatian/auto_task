#!/usr/bin/env python3
"""
sign_nonce.py — 每天为 XTtools 签名防重放 nonce
使用 Gitee Content API (带完整 debug 输出)
"""
import os, sys, json, secrets, base64, datetime, requests
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

GITEE_API_BASE = "https://gitee.com/api/v5"
OWNER = "getime"
REPO = "xttools-tokens"
FILE_PATH = "XTtools/nonce.txt"
PRIV_PATH = "./rsa_private_key.pem"
BRANCH = "master"

def debug(msg):
    print(f"[DEBUG] {msg}", flush=True)

def main():
    # ---- 1. Token 检查 ----
    token = os.getenv("GITEE_TOKEN", "")
    if not token:
        print("[FAIL] GITEE_TOKEN 环境变量未设置或为空")
        sys.exit(1)
    debug(f"token 前 8 位: {token[:8]}... 长度={len(token)}")

    # ---- 2. 私钥 ----
    try:
        with open(PRIV_PATH) as f:
            key = RSA.import_key(f.read())
        debug("私钥加载成功")
    except FileNotFoundError:
        print(f"[FAIL] {PRIV_PATH} 未找到")
        sys.exit(1)

    # ---- 3. 生成 nonce + 签名 ----
    nonce = secrets.token_hex(16)
    today = datetime.date.today().isoformat()
    payload_str = f"{nonce}|{today}"
    h = SHA256.new(payload_str.encode())
    sig = pkcs1_15.new(key).sign(h)
    sig_b64 = base64.b64encode(sig).decode()
    file_content = f"{payload_str}|{sig_b64}"
    content_b64 = base64.b64encode(file_content.encode()).decode()
    debug(f"nonce={nonce} today={today} content_len={len(file_content)}")

    # ---- 4. 构造请求 ----
    url = f"{GITEE_API_BASE}/repos/{OWNER}/{REPO}/contents/{FILE_PATH}"
    debug(f"URL: {url}")

    # ---- 5. 先 GET 获取 sha（文件已存在时需要）----
    sha = None
    try:
        get_url = f"{url}?access_token={token}"
        debug(f"GET {get_url[:80]}...")
        r_get = requests.get(get_url, timeout=15)
        debug(f"GET 响应: {r_get.status_code}")
        if r_get.status_code == 200:
            data = r_get.json()
            if isinstance(data, dict) and "sha" in data:
                sha = data["sha"]
                debug(f"文件已存在, sha={sha[:12]}...")
            else:
                debug(f"GET 返回非 dict: {type(data).__name__} len={len(str(data))}")
        elif r_get.status_code == 404:
            debug("文件不存在, 将新建")
        else:
            debug(f"GET 异常: {r_get.text[:200]}")
    except Exception as e:
        debug(f"GET 异常: {type(e).__name__}: {str(e)[:100]}")

    # ---- 6. PUT/POST ----
    put_data = {
        "content": content_b64,
        "message": f"chore: sign nonce for {today}",
        "branch": BRANCH,
    }
    if sha:
        put_data["sha"] = sha
        method = "PUT"
    else:
        method = "POST"

    debug(f"method={method} sha={'有' if sha else '无'} payload_keys={list(put_data.keys())}")
    debug(f"params: access_token=*** (masked)")
    try:
        if method == "PUT":
            r = requests.put(url, params={"access_token": token}, json=put_data, timeout=15)
        else:
            r = requests.post(url, params={"access_token": token}, json=put_data, timeout=15)
    except Exception as e:
        print(f"[FAIL] 请求异常: {type(e).__name__}: {str(e)[:200]}")
        sys.exit(1)

    debug(f"响应状态码: {r.status_code}")
    debug(f"响应正文: {r.text[:500]}")

    if r.status_code in (201, 200):
        print(f"[OK] Nonce 已写入 {OWNER}/{REPO}/{FILE_PATH}")
        print(f"    nonce={nonce}")
    else:
        print(f"[FAIL] {r.status_code}: {r.text[:500]}")
        # 404 提示
        if r.status_code == 404:
            print(">> 排查方向:")
            print("   1) 仓库名/路径是否正确: getime/xttools-tokens/XTtools/nonce.txt")
            print("   2) Token 是否有 projects 写入权限")
            print("   3) branch 是否确实为 master")
            print("   4) 可用 curl 手动测试见下方")
            print("curl -X POST 'https://gitee.com/api/v5/repos/getime/xttools-tokens/contents/XTtools/nonce.txt?access_token=YOUR_TOKEN' -H 'Content-Type: application/json' -d '{\"content\":\"dGVzdA==\",\"message\":\"test\",\"branch\":\"master\"}'")
        sys.exit(1)

if __name__ == "__main__":
    main()
