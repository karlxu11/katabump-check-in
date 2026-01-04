# Katabump Server Auto Renew | Katabump 自动续期脚本

这是一个运行在 GitHub Actions 上的自动化脚本，用于自动续期 Katabump 面板上的服务器。

它基于 **DrissionPage** 开发，针对 Cloudflare 验证进行了深度优化，能够**自动下载并配置 Silk Privacy Pass Client 插件**，实现零人工干预的自动过盾与续期。

## ✨ 功能特性

* **🛡️ 自动过盾**：脚本启动时自动从 Google 官方下载 **Silk Privacy Pass Client** 插件并挂载，有效通过 Cloudflare 5秒盾。
* **🔑 账号直连**：直接使用 Katabump **邮箱 + 密码** 登录，无需提取复杂的 Token。
* **🔗 灵活配置**：通过 GitHub Secrets 配置目标服务器链接，换服务器或换号无需修改代码。
* **🤖 全自动流程**：下载插件 -> 登录 -> 进入服务器 -> 点击续期 -> 处理弹窗 -> 确认。
* **📸 故障截图**：如果运行失败，会自动上传截图到 GitHub Actions Artifacts，方便排查问题。
* **⏰ 定时运行**：默认每 3 天自动执行一次续期任务。

## 📂 文件结构

* `main.py`: 核心自动化脚本（包含插件下载、解压、自动登录逻辑）。
* `.github/workflows/renew.yml`: GitHub Action 配置文件（定义环境变量与定时任务）。
* `requirements.txt`: Python 依赖列表。

## 🚀 部署指南

### 第一步：准备代码
将本项目的所有文件上传至您的 GitHub 仓库。

### 第二步：配置 GitHub Secrets (关键)
进入您的 GitHub 仓库，依次点击：
`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`。

请添加以下 **3 个** 必须的变量：

| Secret Name (变量名) | Value (值 / 示例) | 说明 |
| :--- | :--- | :--- |
| **KB_EMAIL** | `your_email@example.com` | 您的 Katabump 登录邮箱 |
| **KB_PASSWORD** | `your_password123` | 您的 Katabump 登录密码 |
| **KB_RENEW_URL** | `https://dashboard.katabump.com/servers/edit?id=197288` | **续期页面的完整链接**<br>(请登录面板进入服务器页面复制浏览器地址栏) |

### 第三步：启用与测试
1.  **自动运行**：配置完成后，脚本将按照 `renew.yml` 中的设定（每3天）自动运行。
2.  **手动测试**：
    * 点击仓库上方的 **Actions** 标签。
    * 点击左侧的 **Katabump Auto Renew**。
    * 点击右侧的 **Run workflow** 按钮 -> 再点击绿色的 **Run workflow**。
3.  等待运行完成。成功后日志会显示 `🎉🎉🎉 续期成功！任务完成。`。

## ❓ 常见问题

**Q: 为什么运行失败了？**
A: 请在 Actions 运行详情页面底部下载 **Artifacts (debug-screenshots)**。解压后查看截图：
* `login_fail.jpg`: 登录失败（可能是密码错误或被验证码拦截）。
* `no_renew.jpg`: 未找到续期按钮（可能是服务器不需要续期，或页面加载慢）。
* `crash.jpg`: 脚本崩溃截图。

**Q: 需要手动上传插件吗？**
A: **不需要**。脚本内置了下载器，每次运行时会自动从 Google 官方源下载最新版的 Silk 插件并解压使用。

**Q: 如何修改运行频率？**
A: 修改 `.github/workflows/renew.yml` 文件中的 `cron: '0 2 */3 * *'`。
* `0 2 */3 * *`: 每 3 天运行一次。
* `0 8 * * *`: 每天早上 8 点运行一次。

## ⚠️ 免责声明
本项目仅供学习 DrissionPage 自动化与 GitHub Actions 部署使用。请勿用于恶意滥用或违反 Katabump 服务条款的用途。
