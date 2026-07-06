# Migration From oh_my_reverse_skill

本项目从 `E:/ai_project/oh_my_reverse_skill` 迁移验证码专项内容。

## 来源映射

| 原路径 | 当前路径 |
|---|---|
| `6-验证码逆向层/` | `skills/6-验证码逆向层/` |
| `验证码经验库/` | `experience/验证码经验库/` |
| `tools/captcha*.py` | `tools/` |
| `tools/validate_captcha*.py` | `tools/` |
| `tool-contracts/*captcha*.contract.md` | `tool-contracts/` |
| `tool-contracts/detect_captcha_provider.contract.md` | `tool-contracts/` |
| `datasets/captcha_flywheel/` | `datasets/captcha_flywheel/` |
| CAPTCHA public-range labs | `labs/public-range-labs/` |
| CAPTCHA public-range evidence | `evidence/public-range/` |
| `skills-experience/captcha-*` | `experience/skills-experience/` |
| `authorized-live-tests/reports-redacted/` | `evidence/authorized-live/reports-redacted/` |

## 后续工作

- 重新整理 skills 目录，合并为 service / provider diagnostics / solver contract 三类入口。
- 增加 FastAPI solver 服务。
- 增加 dataset/model/action registry。
- 增加 CI：schema、tool index、dataset、model package、action schema、no-secret、no-large-artifact。
