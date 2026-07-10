#!/usr/bin/env python3
"""腾讯混元生3D (Hunyuan-to-3D Pro) 驱动 —— 图生3D / 文生3D → 下载 GLB。

凭证(绝不硬编码)从下面任一来源读取,优先级:环境变量 > 凭证文件。
  - 环境变量: TENCENT_SECRET_ID / TENCENT_SECRET_KEY
  - 凭证文件: ~/.config/hunyuan/credentials  (KEY=VALUE 每行一个)

接口: ai3d.tencentcloudapi.com  签名: TC3-HMAC-SHA256  默认地域: ap-guangzhou
  SubmitHunyuanTo3DProJob / QueryHunyuanTo3DProJob  Version 2025-05-13
  入参: ImageBase64(≤6MB) | ImageUrl(≤8MB) | Prompt(≤1024) ;
        ResultFormat(OBJ/GLB/STL/USDZ/FBX,默认 obj,glb) ; EnablePBR(bool) ;
        FaceCount(3000-1500000,默认 500000) ; GenerateType(Normal/LowPoly/Geometry/Sketch)

用法:
  submit --image ref.png [--prompt "..."] [--format GLB] [--pbr] [--faces 40000] [--type Normal]
  query  --job <JobId>
  gen    --image ref.png --out out.glb [同 submit 的可选项] [--timeout 600]
  gen    --prompt "一枚中国传统金元宝" --out out.glb
"""
import argparse, base64, hashlib, hmac, json, os, sys, time, urllib.request, urllib.error

HOST = "ai3d.tencentcloudapi.com"
SERVICE = "ai3d"
REGION = "ap-guangzhou"
VERSION = "2025-05-13"
CRED_FILE = os.path.expanduser("~/.config/hunyuan/credentials")


def _load_creds():
    sid = os.environ.get("TENCENT_SECRET_ID")
    skey = os.environ.get("TENCENT_SECRET_KEY")
    if (not sid or not skey) and os.path.exists(CRED_FILE):
        with open(CRED_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k == "TENCENT_SECRET_ID" and not sid:
                    sid = v
                elif k == "TENCENT_SECRET_KEY" and not skey:
                    skey = v
    if not sid or not skey:
        sys.exit("缺少凭证:需要 TENCENT_SECRET_ID + TENCENT_SECRET_KEY"
                 "(环境变量或 " + CRED_FILE + ")。目前只有 SecretId 时无法签名。")
    return sid, skey


def _hmac(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def call(action, payload, version=VERSION):
    sid, skey = _load_creds()
    ts = int(time.time())
    date = time.strftime("%Y-%m-%d", time.gmtime(ts))
    body = json.dumps(payload)
    ct = "application/json; charset=utf-8"
    canonical_headers = "content-type:%s\nhost:%s\nx-tc-action:%s\n" % (ct, HOST, action.lower())
    signed_headers = "content-type;host;x-tc-action"
    hashed_payload = hashlib.sha256(body.encode("utf-8")).hexdigest()
    canonical_request = "POST\n/\n\n%s\n%s\n%s" % (canonical_headers, signed_headers, hashed_payload)
    scope = "%s/%s/tc3_request" % (date, SERVICE)
    hashed_canon = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = "TC3-HMAC-SHA256\n%d\n%s\n%s" % (ts, scope, hashed_canon)
    sd = _hmac(("TC3" + skey).encode("utf-8"), date)
    ss = _hmac(sd, SERVICE)
    sk = _hmac(ss, "tc3_request")
    signature = hmac.new(sk, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = ("TC3-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s"
                     % (sid, scope, signed_headers, signature))
    headers = {
        "Authorization": authorization, "Content-Type": ct, "Host": HOST,
        "X-TC-Action": action, "X-TC-Timestamp": str(ts), "X-TC-Version": version,
        "X-TC-Region": REGION,
    }
    req = urllib.request.Request("https://" + HOST, data=body.encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")))
    rsp = resp.get("Response", resp)
    if isinstance(rsp, dict) and rsp.get("Error"):
        sys.exit("API Error %s: %s" % (rsp["Error"].get("Code"), rsp["Error"].get("Message")))
    return rsp


def _actions(args):
    if getattr(args, "rapid", False):
        return ("SubmitHunyuanTo3DRapidJob", "QueryHunyuanTo3DRapidJob")
    return ("SubmitHunyuanTo3DProJob", "QueryHunyuanTo3DProJob")


def _encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _parse_multiview(values):
    out = []
    for value in values or []:
        if "=" not in value:
            sys.exit("--multiview 需要 VIEW=PATH,例如 --multiview back=back.png")
        view_type, path = value.split("=", 1)
        view_type = view_type.strip()
        path = path.strip()
        if not view_type or not path:
            sys.exit("--multiview 需要 VIEW=PATH,例如 --multiview back=back.png")
        out.append({
            "ViewType": view_type,
            "ViewImageBase64": _encode_file(path),
        })
    return out


def _payload(args):
    p = {}
    if getattr(args, "model", None):
        p["Model"] = args.model
    if getattr(args, "image", None):
        p["ImageBase64"] = _encode_file(args.image)
    if getattr(args, "image_url", None):
        p["ImageUrl"] = args.image_url
    if getattr(args, "prompt", None):
        p["Prompt"] = args.prompt
    multiview = _parse_multiview(getattr(args, "multiview", None))
    if multiview:
        p["MultiViewImages"] = multiview
    if getattr(args, "format", None):
        p["ResultFormat"] = args.format
    if getattr(args, "pbr", False):
        p["EnablePBR"] = True
    if getattr(args, "faces", None):
        p["FaceCount"] = args.faces
    if getattr(args, "type", None):
        p["GenerateType"] = args.type
    if not p.get("ImageBase64") and not p.get("ImageUrl") and not p.get("Prompt"):
        sys.exit("submit 需要 --image / --image-url / --prompt 至少一个")
    return p


def _result_urls(rsp):
    """从查询响应里尽量挖出结果文件 URL(字段名按文档可能为 ResultFile3Ds[].Url)。"""
    out = []
    files = rsp.get("ResultFile3Ds") or rsp.get("ResultFile3D") or rsp.get("File3Ds") or []
    if isinstance(files, dict):
        files = [files]
    for it in files:
        if isinstance(it, dict):
            url = it.get("Url") or it.get("URL") or it.get("FileUrl")
            if url:
                out.append((it.get("Type") or "", url))
    return out


def cmd_submit(args):
    submit_action, _ = _actions(args)
    rsp = call(submit_action, _payload(args))
    print(json.dumps(rsp, ensure_ascii=False))
    if rsp.get("JobId"):
        print("JobId:", rsp["JobId"], file=sys.stderr)


def cmd_query(args):
    _, query_action = _actions(args)
    rsp = call(query_action, {"JobId": args.job})
    print(json.dumps(rsp, ensure_ascii=False))


def cmd_gen(args):
    submit_action, query_action = _actions(args)
    sub = call(submit_action, _payload(args))
    job = sub.get("JobId")
    if not job:
        sys.exit("提交未返回 JobId: " + json.dumps(sub, ensure_ascii=False))
    print("submitted JobId=%s, polling..." % job, file=sys.stderr)
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        q = call(query_action, {"JobId": job})
        status = q.get("Status") or q.get("JobStatus") or ""
        print("  status=%s" % status, file=sys.stderr)
        if str(status).upper() in ("DONE", "SUCCESS", "FINISH", "FINISHED", "5"):
            urls = _result_urls(q)
            if not urls:
                sys.exit("DONE 但未找到结果 URL,原始响应:\n" + json.dumps(q, ensure_ascii=False))
            # prefer the requested format
            want = (args.format or "GLB").upper()
            chosen = next((u for t, u in urls if want in (t or "").upper() or want.lower() in u.lower()), urls[0][1])
            print("downloading:", chosen, file=sys.stderr)
            urllib.request.urlretrieve(chosen, args.out)
            print("saved:", args.out)
            return
        if str(status).upper() in ("FAIL", "FAILED", "ERROR", "4"):
            sys.exit("任务失败: " + json.dumps(q, ensure_ascii=False))
        time.sleep(args.interval)
    sys.exit("轮询超时(%ss),JobId=%s 仍未完成" % (args.timeout, job))


def main():
    ap = argparse.ArgumentParser(description="腾讯混元生3D Pro 驱动")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("submit", "gen"):
        s = sub.add_parser(name)
        s.add_argument("--image")
        s.add_argument("--image-url", dest="image_url")
        s.add_argument("--prompt")
        s.add_argument("--model", help="3.0/3.1")
        s.add_argument("--multiview", action="append", default=[],
                       help="Add a multi-view image as VIEW=PATH, e.g. back=back.png. Repeatable.")
        s.add_argument("--format", default="GLB", help="OBJ/GLB/STL/USDZ/FBX")
        s.add_argument("--pbr", action="store_true")
        s.add_argument("--faces", type=int)
        s.add_argument("--type", help="Normal/LowPoly/Geometry/Sketch")
        s.add_argument("--rapid", action="store_true", help="用 Rapid 快速版(免费额度);默认 Pro 专业版")
        if name == "gen":
            s.add_argument("--out", required=True)
            s.add_argument("--timeout", type=int, default=600)
            s.add_argument("--interval", type=int, default=8)
    q = sub.add_parser("query")
    q.add_argument("--job", required=True)
    q.add_argument("--rapid", action="store_true")
    args = ap.parse_args()
    {"submit": cmd_submit, "query": cmd_query, "gen": cmd_gen}[args.cmd](args)


if __name__ == "__main__":
    main()
