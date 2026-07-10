#!/usr/bin/env python3
"""腾讯混元生3D —— 绑骨(AutoRigging) + 文生动作(Text-to-Motion / HY-Motion-1.0)。
复用 hunyuan3d_gen.py 的 TC3-HMAC-SHA256 签名 call()。全部 Version 2025-05-13。
注意:绑骨/动作的查询端是 Describe* 不是 Query*;产物均为 FBX(下载链有效期 1 天)。

  # 文生动作(纯文本→通用人形带动画 FBX;不传 retarget=通用骨架)
  motion --prompt "双手抱拳,拱手作揖行礼,身体微微前倾鞠躬" --duration 4 --rewrite --out gs.fbx
  # 文生动作重定向到混元绑骨产物(retarget-url 必须是混元绑骨/动画接口产物)
  motion --prompt "..." --retarget-url <url> --retarget-type FBX --out gs.fbx
  # 绑骨(裸网格 URL 直喂,要 A/T-pose 无配饰;可附 1-48 预设动作 MotionType,如 26/27=待机)
  rig --file-url <glb_url> --file-type GLB [--motion-type 26] --out rigged.fbx
  # 原子调试
  submit-motion / describe-motion --job <id> ; submit-rig / describe-rig --job <id>
"""
import argparse, json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hunyuan3d_gen import call, _result_urls  # noqa: E402


def _poll(query_action, job, timeout, interval, out):
    deadline = time.time() + timeout
    while time.time() < deadline:
        q = call(query_action, {"JobId": job})
        st = str(q.get("Status") or q.get("JobStatus") or "").upper()
        print("  status=%s" % st, file=sys.stderr)
        if st in ("DONE", "SUCCESS", "FINISH", "FINISHED"):
            urls = _result_urls(q)
            if not urls:
                sys.exit("DONE 但无结果 URL:\n" + json.dumps(q, ensure_ascii=False))
            for t, u in urls:
                print("  result:", t, u, file=sys.stderr)
            chosen = urls[0][1]
            if out:
                urllib.request.urlretrieve(chosen, out)
                print("saved:", out)
            else:
                print(json.dumps(urls, ensure_ascii=False))
            return q
        if st in ("FAIL", "FAILED", "ERROR"):
            sys.exit("任务失败: " + json.dumps(q, ensure_ascii=False))
        time.sleep(interval)
    sys.exit("轮询超时 job=%s" % job)


def _motion_payload(args):
    p = {"Prompt": args.prompt}
    if args.duration:
        p["Duration"] = args.duration
    if args.retarget_url:
        p["RetargetFile"] = {"Url": args.retarget_url, "Type": args.retarget_type or "FBX"}
    if args.no_mesh:
        p["EnableMesh"] = False
    if args.rewrite:
        p["EnableRewrite"] = True
    if args.duration_est:
        p["EnableDurationEst"] = True
    return p


def _rig_payload(args):
    p = {"File3D": {"Url": args.file_url, "Type": (args.file_type or "GLB").upper()}}
    if args.motion_type:
        p["MotionType"] = args.motion_type
    return p


def main():
    ap = argparse.ArgumentParser(description="混元 绑骨 + 文生动作")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("motion", "submit-motion"):
        s = sub.add_parser(name)
        s.add_argument("--prompt", required=True, help="≤128 字,动作文本描述")
        s.add_argument("--duration", type=int, default=4, help="1-12s,默认4")
        s.add_argument("--retarget-url", dest="retarget_url", help="重定向目标(须混元绑骨/动画产物)")
        s.add_argument("--retarget-type", dest="retarget_type", default="FBX")
        s.add_argument("--no-mesh", dest="no_mesh", action="store_true", help="不带蒙皮 mesh")
        s.add_argument("--rewrite", action="store_true", help="prompt 自动扩写")
        s.add_argument("--duration-est", dest="duration_est", action="store_true")
        if name == "motion":
            s.add_argument("--out")
            s.add_argument("--timeout", type=int, default=600)
            s.add_argument("--interval", type=int, default=8)

    for name in ("rig", "submit-rig"):
        s = sub.add_parser(name)
        s.add_argument("--file-url", dest="file_url", required=True)
        s.add_argument("--file-type", dest="file_type", default="GLB")
        s.add_argument("--motion-type", dest="motion_type", type=int, help="1-48 预设动作;省略=只绑骨")
        if name == "rig":
            s.add_argument("--out")
            s.add_argument("--timeout", type=int, default=600)
            s.add_argument("--interval", type=int, default=8)

    for name, act in (("describe-motion", "DescribeHunyuanTo3DMotionJob"), ("describe-rig", "DescribeAutoRiggingJob")):
        s = sub.add_parser(name)
        s.add_argument("--job", required=True)
        s.set_defaults(_act=act)

    args = ap.parse_args()
    if args.cmd == "submit-motion":
        print(json.dumps(call("SubmitHunyuanTo3DMotionJob", _motion_payload(args)), ensure_ascii=False))
    elif args.cmd == "motion":
        sub_rsp = call("SubmitHunyuanTo3DMotionJob", _motion_payload(args))
        job = sub_rsp.get("JobId") or sys.exit("无 JobId: " + json.dumps(sub_rsp, ensure_ascii=False))
        print("motion JobId=%s polling..." % job, file=sys.stderr)
        _poll("DescribeHunyuanTo3DMotionJob", job, args.timeout, args.interval, args.out)
    elif args.cmd == "submit-rig":
        print(json.dumps(call("SubmitAutoRiggingJob", _rig_payload(args)), ensure_ascii=False))
    elif args.cmd == "rig":
        sub_rsp = call("SubmitAutoRiggingJob", _rig_payload(args))
        job = sub_rsp.get("JobId") or sys.exit("无 JobId: " + json.dumps(sub_rsp, ensure_ascii=False))
        print("rig JobId=%s polling..." % job, file=sys.stderr)
        _poll("DescribeAutoRiggingJob", job, args.timeout, args.interval, args.out)
    elif args.cmd in ("describe-motion", "describe-rig"):
        print(json.dumps(call(args._act, {"JobId": args.job}), ensure_ascii=False))


if __name__ == "__main__":
    main()
