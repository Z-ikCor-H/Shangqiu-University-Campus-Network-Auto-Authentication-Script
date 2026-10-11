#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校园网自动认证脚本 —— Dr.COM 高定制 eportal 协议
==================================================

针对 http://172.25.251.2 的 Dr.COM 认证系统逆向实现。

原理：
  1. 认证状态检测：GET /drcom/chkstatus  （result=1 在线，result=0 需登录）
  2. 登录：          GET /drcom/login     （JSONP，callback 参数必须在最前）
  3. 密码明文提交（该站点 en_md5=0），账号 = 手机号 + 运营商后缀

用法：
  python campus_auth.py              # 检测一次，未登录则登录一次
  python campus_auth.py --once       # 同上
  python campus_auth.py --loop 300   # 每 300 秒检测一次，掉线自动重连
  python campus_auth.py --status     # 只查看当前在线状态，不登录

依赖：pip install requests
配置：同目录 config.json（账号、密码、运营商后缀）
"""

import argparse
import json
import logging
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE = BASE_DIR / "auth.log"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_CONFIG = {
    "server": "172.25.251.2",   # 认证服务器地址
    "username": "",             # 账号（手机号）
    "password": "",             # 密码（明文）
    "suffix": "",               # 运营商后缀：""=校园网，@unicom=联通，@cmcc=移动，@telecom=电信
    "check_interval": 60,       # --loop 模式默认检测间隔（秒）
    "timeout": 8,               # 请求超时（秒）
    "user_agent": DEFAULT_USER_AGENT,
}

# Dr.COM 登录失败常见 msg 码
MSG_HINTS = {
    1: "账号或密码错误",
    2: "账号已停机或欠费",
    3: "账号已在线",
    6: "MAC/IP/NAS 参数错误",
}

# 不在校园网时的检测间隔（秒），避免离校后每 30 秒空转
IDLE_INTERVAL = 300


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logging.warning("未找到 config.json，已生成默认配置模板，请填写账号密码后重新运行。")
        sys.exit(1)
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg


def _jsonp_get(session: requests.Session, url: str, params, timeout: int):
    """发送 JSONP GET 请求，callback 参数放在最前面（该服务器对参数顺序敏感）。"""
    callback = "dr" + str(random.randint(100000, 999999))
    pairs = [("callback", callback)]
    pairs += [(k, v) for k, v in params]
    pairs += [("v", str(random.randint(500, 10499))), ("lang", "zh")]

    qs = "&".join(f"{quote(k)}={quote(str(v))}" for k, v in pairs)
    try:
        r = session.get(url + "?" + qs, timeout=timeout)
    except requests.RequestException as e:
        logging.debug("请求异常：%s", e)
        return None

    r.encoding = "utf-8"
    text = r.text.strip()
    start = text.find("(")
    end = text.rfind(")")
    if start == -1 or end <= start:
        logging.debug("无法解析响应：%s", text[:120])
        return None
    try:
        return json.loads(text[start + 1:end])
    except json.JSONDecodeError:
        logging.debug("JSON 解析失败：%s", text[:120])
        return None


def check_online(cfg: dict, session: requests.Session):
    """检测认证状态。返回 True(在线) / False(需登录) / None(连不上认证服务器)。"""
    url = f"http://{cfg['server']}/drcom/chkstatus"
    data = _jsonp_get(session, url, [("jsVersion", "4.X")], cfg["timeout"])
    if data is None:
        return None
    return data.get("result") == 1


def do_login(cfg: dict, session: requests.Session):
    """发起登录。返回 True(成功) / False(失败) / None(连不上服务器)。"""
    if not cfg["username"] or not cfg["password"]:
        logging.error("config.json 中未填写 username / password，无法登录。")
        return False

    account = cfg["username"] + cfg.get("suffix", "")
    url = f"http://{cfg['server']}/drcom/login"
    params = [
        ("DDDDD", account),
        ("upass", cfg["password"]),
        ("0MKKey", "123456"),
        ("R1", "0"),
        ("R2", ""),
        ("R3", "0"),
        ("R6", "0"),
        ("para", "00"),
        ("v6ip", ""),
        ("terminal_type", "1"),
        ("lang", "zh-cn"),
        ("jsVersion", "4.X"),
    ]
    data = _jsonp_get(session, url, params, cfg["timeout"])
    if data is None:
        return None

    result = data.get("result")
    if result == 1 or result == "ok":
        logging.info("✅ 登录成功，账号：%s", account)
        return True

    msg = data.get("msg")
    hint = MSG_HINTS.get(msg, f"未知错误码 {msg}")
    logging.warning("登录失败（%s），账号：%s", hint, account)
    return False


def run_status(cfg: dict, session: requests.Session):
    state = check_online(cfg, session)
    if state is True:
        logging.info("当前已在线（已认证）。")
    elif state is False:
        logging.info("当前未登录，需要认证。")
    else:
        logging.info("连不上认证服务器 %s，可能不在校园网内。", cfg["server"])


def main():
    parser = argparse.ArgumentParser(description="校园网自动认证脚本（Dr.COM）")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--status", action="store_true", help="只查看当前在线状态，不登录")
    group.add_argument("--once", action="store_true", help="检测一次，未登录则登录一次")
    group.add_argument("--loop", type=int, metavar="秒", help="循环检测并自动重连")
    args = parser.parse_args()

    handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
    if sys.stdout is not None:  # pythonw 后台运行无控制台时，跳过控制台输出，避免写 None 报错
        handlers.insert(0, logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )

    cfg = load_config()
    session = requests.Session()
    session.headers["User-Agent"] = cfg.get("user_agent", DEFAULT_USER_AGENT)

    if args.status:
        run_status(cfg, session)
        return

    if args.loop and args.loop > 0:
        logging.info(
            "进入循环模式：校园网内每 %d 秒检测，不在校园网时每 %d 秒检测（Ctrl+C 退出）。",
            args.loop, IDLE_INTERVAL,
        )
        was_off_campus = False
        while True:
            state = check_online(cfg, session)
            if state is False:
                logging.info("检测到未登录，尝试认证……")
                do_login(cfg, session)
                interval = args.loop
                was_off_campus = False
            elif state is True:
                interval = args.loop
                was_off_campus = False
            else:
                interval = IDLE_INTERVAL
                if not was_off_campus:
                    logging.info("未连接校园网，进入休眠（每 %d 秒检测），连上校园网后自动恢复。", IDLE_INTERVAL)
                    was_off_campus = True
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                logging.info("已退出。")
                return

    # 默认 / --once：检测一次，未登录则登录一次
    state = check_online(cfg, session)
    if state is True:
        logging.info("已在线，无需认证。")
        return
    if state is None:
        logging.info("连不上认证服务器 %s，请确认已连接校园网 WiFi。", cfg["server"])
        return
    logging.info("未登录，尝试认证……")
    do_login(cfg, session)


if __name__ == "__main__":
    main()
