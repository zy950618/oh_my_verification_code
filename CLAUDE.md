# oh_my_verifty_code — Claude 工作指南

本仓库是验证码专项 SKILLS / 工程库，从 `oh_my_reverse_skill` 拆分。

## 首要原则

- 仅处理授权测试、防御研究、本地靶场、公开允许靶场、自有系统。
- 不帮助未授权绕过真实生产 CAPTCHA/WAF/风控。
- 坐标、角度、滑块距离、动作轨迹只能作为本地/授权验证输出，不能直接声明第三方站点自动通过。
- 所有结论必须标注事实等级：`observed` / `derived` / `assumed` / `unverified`。
- CAPTCHA 成功能力必须以最终业务 API 后端接受证据为准，不能以 challenge endpoint、provider test key、HTTP 200 或本地模型预测成功替代。

## 目标交付

- FastAPI solver service：`/classify`、`/solve`、`/plan-action`。
- 统一输出：`points`、`tiles`、`offset`、`angle`、`track`、`press`、`text`。
- solver registry / model registry / dataset registry / action schema。
- 本地与授权靶场训练。
- 失败样本、数据集、模型评测闭环。

## 必须保留的边界

拒绝或降级以下请求：

- 未授权生产站点验证码绕过。
- stealth、webdriver 隐藏、指纹伪造、clearance cookie 复用。
- 伪造真实风控 token 或访问控制参数。
- 把 `unverified` 结果包装成 `observed`。
- 删除唯一证据但未迁移。

## GitHub 上传原则

只提交规范、源码、schema、脱敏示例、CI。

不要提交 raw HAR、cookie/token、浏览器 profile、模型权重、checkpoints、私有目标、未脱敏 evidence。
