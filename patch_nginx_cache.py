#!/usr/bin/env python3
"""Frigate 派生镜像补丁 2：/assets/Live-*.js 缓存策略改为 no-cache（每次回源校验）。

背景：Live-*.js 的 WebRTC 补丁保持原文件名（内容变、hash 名不变），而 Frigate 的
nginx 对 /assets/ 下发「1 年强缓存」（expires 1y + Cache-Control: public）→ 补丁上线
后，此前访问过的浏览器/主屏 PWA 会长期继续使用缓存里的旧版 JS（表现为：其它设备已
WebRTC、它仍是 MSE；服务端日志看不到该文件的任何再请求）。

做法：在 `location / { ... }` 内、与 `location /assets/` **平级**加一条正则 location，
只命中 Live-*.js，覆写缓存策略为 `expires off + Cache-Control: no-cache`：
  - 普通资源（/assets/ 其余、fonts、locales）缓存策略不变；
  - 被命中文件浏览器每次加载都会带 If-None-Match 回源，未变 → 304（开销可忽略），
    有变 → 自动取新。此后任何补丁/上游重建都无需再挨个设备清缓存。
  - 注意：**正则必须是同层级**——实测三级嵌套（/assets/ 块内再嵌正则）不参与匹配；
    同层正则（与上游自己的 webmanifest 正则同形态）按顺序检查、命中即胜出。

锚点守卫：找不到 /assets/ 块、或块内容不符合预期 → 非零码退出（CI 失败告警），
需重新核对容器内 /usr/local/nginx/conf/nginx.conf 再更新本脚本。
"""
import os
import sys

CONF = os.environ.get("NGINX_CONF", "/usr/local/nginx/conf/nginx.conf")
ANCHOR = "            location /assets/ {"
MARKER = "location ~ ^/assets/.*Live-"
OLD_MARKS = ('expires 1y;', 'add_header Cache-Control "public";')
SIBLING = [
    "",
    "            location ~ ^/assets/.*Live-.*\\.js$ {",
    "                expires off;",
    '                add_header Cache-Control "no-cache";',
    "            }",
]


def main() -> None:
    src = open(CONF, encoding="utf-8").read()
    if MARKER in src:
        print("[patch2] 已打过（同层正则在位），跳过")
        return
    if src.count(ANCHOR) != 1:
        print(f"[patch2] FAIL: 锚点 {ANCHOR!r} 命中 {src.count(ANCHOR)} 次（预期 1）")
        sys.exit(1)
    lines = src.split("\n")
    idx = next(i for i, l in enumerate(lines) if l == ANCHOR)
    j = idx + 1
    while lines[j].strip() != "}":
        j += 1
    block = "\n".join(lines[idx : j + 1])
    for mark in OLD_MARKS:
        if mark not in block:
            print(f"[patch2] FAIL: /assets/ 块内未找到 {mark!r}，块内容与预期不符")
            sys.exit(1)
    out = lines[: j + 1] + SIBLING + lines[j + 1 :]
    with open(CONF, "wb") as fh:
        fh.write("\n".join(out).encode("utf-8"))
    print(f"[patch2] OK: 已为 Live-*.js 覆写缓存策略（写在 {CONF}，{len(lines)} -> {len(out)} 行）")


if __name__ == "__main__":
    main()
