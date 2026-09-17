# Frigate 派生镜像：把 Live UI 的直播模式强制为 WebRTC
# - base 默认跟随本地使用的镜像源（可用 Repository variable BASE_IMAGE 覆盖）
# - 补丁脚本带锚点守卫：上游重构 web 代码 → 构建失败告警，而非静默失效
ARG BASE_IMAGE=docker.cnb.cool/frigate-cn/frigate:stable-rocm
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.source="https://github.com/jazzzzmaybe/frigate-image"

COPY patch_live_js.py /tmp/patch_live_js.py
RUN python3 /tmp/patch_live_js.py && rm -f /tmp/patch_live_js.py

COPY patch_nginx_cache.py /tmp/patch_nginx_cache.py
RUN python3 /tmp/patch_nginx_cache.py && rm -f /tmp/patch_nginx_cache.py
