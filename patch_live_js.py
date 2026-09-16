#!/usr/bin/env python3
"""Frigate 派生镜像补丁：把 Live UI 的直播模式强制为 WebRTC（替代默认 MSE 优先）。

原理：Frigate 前端用 `"MediaSource" in window` 探测浏览器 MSE 能力，能则给
restream（go2rtc）相机选 "mse"，否则选 "webrtc"。本脚本把三个决策点中的该探测
改成恒假，于是所有 restream 相机在 Live 页一律走 WebRTC。作用范围仅限**直播选路**；
HLS 回放（片段/事件播放）等功能不受影响。

三个决策点（Live-*.js 内）：
  1. 全局 hook（仪表盘所有格子）的 mseSupported 计算（主 effect）
  2. 全局 hook 的 reset 回调（"重置直播模式"按钮）
  3. 单相机视图自己的选择器（打开大画面用）

锚点失效（上游重构 web 代码）时脚本以非零码退出 → CI 构建失败告警；
此时需要重新分析容器内 /opt/frigate/web/assets/Live-*.js 并更新本脚本。
"""
import glob
import os
import re
import sys

ASSETS = os.environ.get("FRIGATE_WEB_ASSETS", "/opt/frigate/web/assets")
MS = r'"MediaSource"in window\|\|"ManagedMediaSource"in window'


def apply_once(src: str, pattern: str, repl: str, label: str) -> str:
    hits = re.findall(pattern, src)
    if len(hits) != 1:
        print(f"[patch] FAIL {label}: 锚点命中 {len(hits)} 次（预期 1 次）")
        sys.exit(1)
    out = re.sub(pattern, repl, src, count=1)
    print(f"[patch] OK   {label}")
    return out


def main() -> None:
    files = sorted(glob.glob(os.path.join(ASSETS, "Live-*.js")))
    if len(files) != 1:
        print(f"[patch] FAIL: 预期 1 个 Live-*.js，实际 {len(files)} 个: {files}")
        sys.exit(1)
    path = files[0]
    src = open(path, encoding="utf-8").read()
    before = len(src)

    # 1) 全局 hook 主 effect：const X=MS...,A={},B={},C={}  →  const X=!1,...
    src = apply_once(
        src,
        r"=" + MS + r"(?=,[A-Za-z_$][\w$]*=\{\},[A-Za-z_$][\w$]*=\{\},[A-Za-z_$][\w$]*=\{\})",
        "=!1",
        "hook(主 effect) mseSupported 恒假",
    )
    # 2) 全局 hook 的 reset 回调：const X=MS...,v=t.find(  →  const X=!1,...
    src = apply_once(
        src,
        r"=" + MS + r"(?=,[A-Za-z_$][\w$]*=t\.find\()",
        "=!1",
        "hook(reset) mseSupported 恒假",
    )
    # 3) 单相机视图：MS?v?"mse":"jsmpeg":"webrtc"  →  v?"webrtc":"jsmpeg"
    src = apply_once(
        src,
        MS + r'\?([A-Za-z_$][\w$]*)\?"mse":"jsmpeg":"webrtc",\[',
        r'\1?"webrtc":"jsmpeg",[',
        "单相机视图 选择分支 → webrtc",
    )

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    remain = src.count('"MediaSource"in window')
    print(f"[patch] 完成: {path} ({before} -> {len(src)} bytes, 剩余 MS 探测 {remain} 处=birdseye/渲染分支，未动)")


if __name__ == "__main__":
    main()
