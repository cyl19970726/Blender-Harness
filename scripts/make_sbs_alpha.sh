#!/usr/bin/env bash
# 把带 alpha 的素材打成 SBS(左RGB|右alpha)H.264 .mp4 —— 给 sbs-alpha-video 组件用。
# 为什么 SBS 而非 VP9/HEVC-alpha:WebKit 上传 WebGL 纹理时丢 alpha,SBS 把 alpha 编进右半幅当 luma 绕开(spike 报告已删,git 历史 @03940cf8 见 docs/research/ar-magnet/透明视频贴卡-spike报告.md)。
# 用法:
#   bash scripts/make_sbs_alpha.sh frames/%03d.png out.mp4 [size] [fps]   # RGBA 序列帧
#   bash scripts/make_sbs_alpha.sh src.mov out.mp4 [size] [fps]          # 带 alpha 的 ProRes4444/.mov
set -euo pipefail
IN="${1:?输入:RGBA序列帧(frames/%03d.png)或带alpha的.mov}"
OUT="${2:?输出 mp4}"
SIZE="${3:-480x480}"      # 单边尺寸(成片宽=2×)
FPS="${4:-24}"
case "$IN" in *%*|*.png|*.PNG) INARGS=(-framerate "$FPS" -i "$IN") ;; *) INARGS=(-i "$IN") ;; esac
ffmpeg -y "${INARGS[@]}" -filter_complex \
"color=c=black:s=${SIZE}:r=${FPS}[bg];[0:v]format=rgba[fg];[bg][fg]overlay=shortest=1,format=yuv420p[L];[0:v]alphaextract,format=yuv420p[R];[L][R]hstack=inputs=2[out]" \
-map "[out]" -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart -an "$OUT"
echo "SBS 成片 -> $OUT (左RGB|右alpha,直通alpha)"
