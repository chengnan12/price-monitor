# 电商价格监控系统

监控京东/淘宝/天猫商品价格，降价时自动发邮件通知。可搭配系统定时任务实现全自动巡检。

## 功能清单

| 功能 | 说明 |
|------|------|
| 多平台支持 | 京东、淘宝、天猫商品页价格抓取 |
| 价格历史追踪 | 每次巡检记录价格，保留近30条历史 |
| 邮件预警 | 价格低于目标价自动发邮件提醒 |
| 命令行管理 | add/list/check/remove 四个命令搞定日常操作 |

## 项目结构

```
price-monitor/
├── monitor.py           # 主程序
├── requirements.txt
├── README.md
├── products.json        # 监控商品列表（运行后自动生成）
└── config.json          # 邮件配置（运行 config 命令生成）
```

## 快速开始

```bash
pip install -r requirements.txt
python monitor.py
```

### 添加监控

```bash
python monitor.py add 机械键盘 https://item.jd.com/1000123456.html 299
```

### 查看列表

```bash
python monitor.py list
# 输出：
# 序号  商品名称         当前价     目标价      状态
# 1     机械键盘         ¥399.00    ¥299.00    监控中
```

### 执行巡检

```bash
python monitor.py check
```

价格低于目标价时会自动发送邮件提醒。

### 配置邮件通知

```bash
python monitor.py config
```

按提示填入邮箱信息（QQ邮箱需开启SMTP服务并获取授权码）。

### 搭配定时任务

将 `python monitor.py check` 加入系统计划任务，每小时自动巡检一次。

## 反爬处理

- 请求间隔随机延迟 1-3 秒
- 模拟浏览器 User-Agent
- 价格解析做异常兜底，单条失败不影响其他商品

## 技术栈

Python 3.9+ · Requests · BeautifulSoup4 · SMTP
