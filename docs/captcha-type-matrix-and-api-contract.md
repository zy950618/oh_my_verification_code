# 验证码类型矩阵与 FastAPI 契约蓝图

## 目标

本文件定义 `oh_my_verifty_code` 的验证码类型覆盖、输出格式、合规边界和 FastAPI contract。

## 类型矩阵

| 大类 | 代表厂商/场景 | 输出形态 | 可纯算性 | 备注 |
|---|---|---|---|---|
| 文本 OCR | 传统图形码、自建 CAPTCHA | `text` | 高 | 完整验证仍依赖 session/token |
| 算术/逻辑题 | 自建站点 | `text` / `answer` | 高到中 | 认证场景需可访问替代 |
| 图片九宫格 | reCAPTCHA v2、hCaptcha | `tiles` / `points` | 视觉答案可模型化，完整验证不可纯算 | 依赖 provider token |
| 空间推理 | hCaptcha、Arkose、复杂点选 | `points` / `tiles` | 中 | 需要视觉/语言/空间推理模型 |
| 点选文字/图标 | 极验、阿里、网易易盾、顶象、数美 | `points` | 中 | 顺序、轨迹、token 绑定 |
| 滑块拼图 | 极验、腾讯、阿里、网易易盾、数美、顶象 | `offset` / `track` | 缺口可纯算，完整验证不可纯算 | 轨迹和设备信号重要 |
| 旋转验证码 | 小红书类、极验/阿里/网易变体 | `angle` / `offset` | 角度可模型化 | 完整验证绑定行为 |
| 按压/长按 | 拼多多类、阿里按压 | `press` / `events` | 低 | 依赖触控时序/压力/环境 |
| 无感/评分 | reCAPTCHA v3/Enterprise、Turnstile | `token/score` | 不可纯算 | 只做 observation/authorized flow |
| 音频 CAPTCHA | Google/hCaptcha 等 | `text` | ASR 可辅助 | 仍有可访问性负担 |
| WAF 托管挑战 | Cloudflare/Akamai/Imperva/DataDome | `risk_state` | 不可纯算 | 不属于坐标 solver，需授权边界 |

## FastAPI Contract

### `/classify`

输入挑战资产与上下文，输出 provider/type 判断。

```json
{
  "provider": "shumei|geetest|aliyun|recaptcha|hcaptcha|turnstile|xiaohongshu|pinduoduo|unknown",
  "challenge_family": "slider|rotate|click|grid|text|press|risk_score|logic",
  "confidence": 0.93,
  "required_solver": "pure|vision_model|action_planner|human_review|unsupported",
  "accessibility_risk": {
    "sensory": true,
    "cognitive": true,
    "motor": false,
    "language": false,
    "transcription": false
  }
}
```

### `/solve`

返回答案、坐标、角度、滑块距离或文本。

```json
{
  "status": "solved|needs_action|human_review|unsupported|blocked",
  "solution_type": "text|points|tiles|offset|angle|track|press",
  "result": {
    "points": [{"x": 123, "y": 88}],
    "offset_x": 142,
    "angle": 37,
    "tiles": [1, 4, 7],
    "text": "A7K9"
  },
  "confidence": 0.91,
  "evidence": {
    "solver": "slider_geometry_v1",
    "model": "captcha-click-yolo-v1",
    "dataset_version": "2026-07",
    "input_hash": "..."
  },
  "accessibility_notes": [
    "visual_challenge_requires_alternative_modality"
  ],
  "safe_use_boundary": "local_lab_or_authorized_testing_only"
}
```

### `/plan-action`

将答案转换为动作计划，仅限本地/授权环境。

```json
{
  "action_schema": "click|drag|press|rotate|type",
  "actions": [
    {"type": "move", "x": 100, "y": 200, "t": 0},
    {"type": "down", "x": 100, "y": 200, "t": 120},
    {"type": "move", "x": 242, "y": 200, "t": 760},
    {"type": "up", "x": 242, "y": 200, "t": 820}
  ],
  "risk_notes": [
    "仅用于本地靶场或授权测试",
    "动作计划不等同第三方生产站点自动通过"
  ]
}
```

## Accessibility & Compliance Gate

依据 W3C / WCAG：

- CAPTCHA 作为确认人类访问的非文本内容，必须有目的说明。
- 每种 CAPTCHA 都可能让某些残障用户无法完成。
- 视觉、音频、交互、认知类 CAPTCHA 都可能造成 sensory/cognitive/motor/language/transcription 负担。
- 认证场景不能只依赖认知型 CAPTCHA，应提供非认知替代方式。
- 无感验证降低交互负担，但会引入隐私、浏览器信号和设备信号依赖。

参考来源：

- W3C Group Draft Note: Inaccessibility of CAPTCHA — https://www.w3.org/TR/turingtest/
- WCAG 2.2 Recommendation — https://www.w3.org/TR/WCAG22/#non-text-content
- WAI Understanding SC 1.1.1 — https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html
- WAI Understanding SC 1.4.7 — https://www.w3.org/WAI/WCAG22/Understanding/low-or-no-background-audio.html
- WAI Understanding SC 3.3.8 — https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html
