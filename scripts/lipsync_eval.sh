#!/usr/bin/env bash
# 口型评审外层 driver(部署前必跑)。串起三件套的【渲染+闸】部分:
#   Tier A 绑骨闸(Blender) -> Tier A 信号闸(host) -> 运动渲染 filmstrip(Blender) -> 拼图
# 然后打印 Tier B(workflow)的启动命令(双模型对抗读这些产物)。
# 前提:Blender app 开着 blender-mcp(socket 9876),且场景里有 Armature+mixamorig:Jaw。
# 用法: bash scripts/lipsync_eval.sh [narration.mp3]
set -uo pipefail
cd "$(dirname "$0")/.."
MP3="${1:-public/ar/magnets/gongfucha/narration.mp3}"
PY=/Users/hhh0x/miniconda3/bin/python3
NODE=$(ls -d ~/.nvm/versions/node/v2*/bin/node 2>/dev/null | sort -V | tail -1)

echo "### 1/4 Tier A 绑骨闸 (Blender scrub)"
$PY scripts/blender_cmd.py exec scripts/bl_lipsync_rig_eval.py 2>&1 | grep -viE "Experimental|trace-warn" | grep -iE "RIG EVAL|\[OK\]|\[XX\]"

echo "### 2/4 Tier A 信号闸 (offline RMS->jaw)"
$PY scripts/lipsync_invariants.py "$MP3" /tmp/rig_report.json /tmp/lipsync
GATE=$?

echo "### 3/4 运动渲染 filmstrip (Blender)"
$PY scripts/blender_cmd.py exec scripts/bl_lipsync_filmstrip.py 2>&1 | grep -viE "Experimental|trace-warn" | grep -iE "FILMSTRIP|degs:"

echo "### 4/4 拼 filmstrip"
NODE_PATH=$(npm root) "$NODE" -e '
const sharp=require("sharp"),fs=require("fs");
(async()=>{
  const meta=JSON.parse(fs.readFileSync("/tmp/film_meta.json"));
  const lbl=(t)=>Buffer.from(`<svg width="180" height="22"><rect width="180" height="22" fill="black"/><text x="4" y="16" fill="#7CFC00" font-size="14" font-family="sans-serif">${t}</text></svg>`);
  const tiles=await Promise.all(meta.map(async m=>sharp(await sharp(`/tmp/film_${String(m.k).padStart(2,"0")}.png`).resize(180,180).toBuffer()).composite([{input:lbl(`${m.t}s ${m.deg}deg`),top:0,left:0}]).toBuffer()));
  const cols=tiles.length, W=180*cols;
  await sharp({create:{width:W,height:180,channels:3,background:"#222"}}).composite(tiles.map((t,i)=>({input:t,top:0,left:180*i}))).png().toFile("/tmp/lipsync_filmstrip.png");
  console.log("filmstrip -> /tmp/lipsync_filmstrip.png");
})().catch(e=>{console.error(e.message);process.exit(1)});'

echo ""
echo "=== 产物 ==="
echo "  曲线图   /tmp/lipsync_curve.png"
echo "  运动排   /tmp/lipsync_filmstrip.png"
echo "  报告     /tmp/lipsync_report.json   (Tier A gate exit=$GATE: 0=PASS)"
echo ""
echo "=== Tier B(部署前最后一关):双模型对抗读运动渲染 ==="
echo "TIERA=\$(python3 -c \"import json;d=json.load(open('/tmp/lipsync_report.json'));print('gate='+d['gate']+'; fails='+str([c['name'] for c in d['checks'] if not c['pass']]))\")"
echo "harness workflow run-script workflows/lipsync-eval-loop.star \\"
echo "  --args \"\$(python3 -c 'import json;print(json.dumps({\"filmstrip\":\"/tmp/lipsync_filmstrip.png\",\"curve\":\"/tmp/lipsync_curve.png\",\"tierA\":open(\"/tmp/lipsync_report.json\").read(),\"context\":\"揭小贤潮汕Q版吉祥物大头,1-DOF下巴骨+音频振幅驱动口型,AR里角色不大、一次性旁白\"}))')\" \\"
echo "  --start-runtime --progress"
exit $GATE
