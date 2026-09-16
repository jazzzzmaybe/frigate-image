# frigate-image

Frigate 派生镜像：在基础镜像之上把 **Live UI 的直播模式强制为 WebRTC**（替代官方默认的 MSE 优先），用于降低直播延迟、减少浏览器端 MSE 丢帧与"漂离实时"问题。

- `patch_live_js.py` — 构建期补丁。带**锚点守卫**：上游 web 代码结构变化导致锚点对不上时，构建直接失败（而非静默失效），届时需重新分析 `/opt/frigate/web/assets/Live-*.js` 并更新锚点。
- CI（GitHub Actions）：push / 每日 04:00（北京时间）检查上游 digest（无变化自动跳过）/ 手动触发。
- 产物：`ghcr.io/jazzzzmaybe/frigate-image:stable-rocm`，由 Unraid 上的 watchtower 自动跟踪更新。

## 维护

- 上游发新版 → 次日 CI 自动重建（补丁自动应用到新 bundle）→ watchtower 自动部署，全程无人值守。
- 若构建失败（`[patch] FAIL ...`）：上游改了 web 代码，更新 `patch_live_js.py` 的锚点即可。
- 回退：把使用方的 compose 镜像引用换回原镜像。
