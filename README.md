# 电商价格监控系统

自动监控京东/淘宝商品价格，降价时邮件通知。

## 功能

- 添加商品监控 URL + 目标价格
- 自动抓取实时价格并记录历史
- 价格低于目标价时发送邮件提醒
- 价格走势追踪（最高/最低/当前）

## 快速开始

```bash
pip install requests beautifulsoup4
python monitor.py
```

## 命令

```bash
# 添加监控
python monitor.py add 机械键盘 https://item.jd.com/123456.html 299

# 查看列表
python monitor.py list

# 执行巡检
python monitor.py check

# 移除监控
python monitor.py remove 1

# 配置邮件通知（QQ邮箱需开启SMTP获取授权码）
python monitor.py config
```

## 搭配定时任务

Windows 计划任务 / Linux crontab 定时执行 `python monitor.py check`，实现全自动监控。

## 技术栈

Python · Requests · BeautifulSoup4 · SMTP · 反爬策略
