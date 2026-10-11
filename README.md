# 校园网自动认证脚本（Dr.COM）

针对学校 Dr.COM 认证系统（`http://172.25.251.2`）的自动登录脚本，检测到掉线后自动重新认证，支持循环常驻与开机自启。

> 📖 完全没写过代码、不知道怎么配置？请看一步步图文教程：[部署教程（小白向）](部署教程.md)

## 功能

- 检测当前在线状态（`--status`）
- 单次检测并登录（`--once`，默认行为）
- 循环检测、掉线自动重连（`--loop 秒`）
- 不在校园网时自动休眠、回到校园网后自动恢复
- Windows 开机自启（计划任务 / 启动目录）

## 环境

- Python 3.9+
- 依赖安装：`pip install -r requirements.txt`

## 快速开始

1. 复制配置模板并填写自己的账号信息：

   ```bash
   cp config.example.json config.json
   ```

   编辑 `config.json`：

   | 字段 | 说明 | 示例 |
   |------|------|------|
   | `server` | 认证服务器地址 | `172.25.251.2` |
   | `username` | 账号（手机号） | `13800138000` |
   | `password` | 密码（明文） | `你的密码` |
   | `suffix` | 运营商后缀 | 校园网留空 `""`，联通 `@unicom`，移动 `@cmcc`，电信 `@telecom` |

   > 登录账号 = `username` + `suffix`。例如联通用户填 `@unicom`。

2. 运行：

   ```bash
   # 只查看当前在线状态
   python campus_auth.py --status

   # 检测一次，未登录则登录一次
   python campus_auth.py --once

   # 每 300 秒检测一次，掉线自动重连
   python campus_auth.py --loop 300
   ```

   日志同时输出到屏幕和 `auth.log`。

## 开机自启（可选）

- **Windows 计划任务（推荐）**：以管理员身份运行 `setup_autostart.ps1`，会创建「登录时」触发的 `CampusAuth` 计划任务，后台运行 `--loop 30`。
- 手动方式：任务计划程序 → 创建任务 → 触发器选"登录时" → 操作填 `python` 和 `campus_auth.py --loop 300` 的完整路径。
- 或 `pyinstaller -F campus_auth.py` 打包成 exe 放入启动目录（`Win+R` 输入 `shell:startup`）。

## 协议说明（已逆向）

针对 Dr.COM 高定制 eportal 的认证流程：

- 认证状态：`GET /drcom/chkstatus`，返回 `result=1`（在线）/ `0`（未登录）
- 登录：`GET /drcom/login`，JSONP，**`callback` 参数必须放在最前**，密码明文（`en_md5=0`）
- 登录字段：`DDDDD`（账号）、`upass`（密码）、`0MKKey=123456`、`R1=0`、`R2`、`R3=0`、`R6=0`、`para=00`、`v6ip`

## 安全提示

- `config.json` 存放明文密码，已加入 `.gitignore`，**请勿提交到公开仓库**。
- 仅用于个人校园网账号，请遵守学校网络使用规定。

## 许可证

[MIT License](LICENSE)
