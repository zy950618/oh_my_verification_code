# oh_my_verifty_code

验证码专项 SKILLS 与工程项目。

本项目从 `oh_my_reverse_skill` 拆分而来，专门承载验证码/验证服务相关能力：

- 市面验证码类型矩阵
- 纯算求解器与视觉模型
- FastAPI 坐标/动作接口
- 本地/授权靶场训练
- 数据集、标签、模型、评测飞轮
- solver / model / action / dataset registry
- accessibility、redaction、authorization 与 refusal 边界

## 边界

本项目只用于授权安全测试、防御研究、本地靶场、公开允许靶场和自有系统验证。

不提供：

- 未授权生产站点验证码绕过
- stealth / webdriver 隐藏
- 指纹伪造
- clearance cookie 复用
- 第三方 solver 平台调用
- 未授权风控 token 伪造

## 目录

| 目录 | 说明 |
|---|---|
| `skills/` | 验证码相关 SKILL |
| `tools/` | captcha solver / dataset / model / validation 工具 |
| `tool-contracts/` | 工具接口契约 |
| `experience/` | 验证码经验库与失败样本经验 |
| `evidence/` | 脱敏 evidence / reports / manifests |
| `datasets/` | 数据集 manifest / labels / splits / evals |
| `labs/` | 本地/授权靶场源码 |
| `docs/` | 类型矩阵、FastAPI schema、合规与迁移文档 |

## GitHub 上传原则

只上传：规范、schema、SKILL、eval、工具源码、脱敏最小示例、README、CI。

不上传：raw HAR、cookie/token、浏览器 profile、模型权重、checkpoints、私有目标、未脱敏 reports、真实账号态、生产 evidence。
