"""
电商价格监控系统
================

监控指定商品价格，降价时发送邮件预警。支持京东、淘宝（示例演示）。
可用于抢购提醒、优惠追踪、竞品监控。

GitHub: https://github.com/chengnan12/price-monitor

用法:
  python monitor.py add <商品名称> <URL> <目标价>
  python monitor.py list
  python monitor.py check
  python monitor.py remove <编号>
"""
import json
import smtplib
import time
import random
import sys
import os
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_FILE = Path(__file__).parent / "products.json"
CONFIG_FILE = Path(__file__).parent / "config.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class PriceMonitor:
    """价格监控核心类"""

    def __init__(self):
        self.products = self._load_products()
        self.config = self._load_config()

    def _load_products(self) -> list:
        if DATA_FILE.exists():
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return []

    def _save_products(self):
        DATA_FILE.write_text(
            json.dumps(self.products, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _load_config(self) -> dict:
        default = {
            "smtp_host": "smtp.qq.com",
            "smtp_port": 587,
            "sender": "",
            "password": "",
            "receiver": "",
            "check_interval": 3600  # 秒
        }
        if CONFIG_FILE.exists():
            default.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        return default

    def add(self, name: str, url: str, alert_price: float) -> int:
        """添加监控商品"""
        product = {
            "id": len(self.products) + 1,
            "name": name,
            "url": url,
            "alert_price": alert_price,
            "current_price": None,
            "lowest_price": None,
            "status": "监控中",
            "created_at": str(datetime.now()),
            "history": []
        }
        self.products.append(product)
        self._save_products()
        return product["id"]

    def remove(self, pid: int) -> bool:
        """移除监控"""
        for i, p in enumerate(self.products):
            if p["id"] == pid:
                self.products.pop(i)
                self._save_products()
                return True
        return False

    def fetch_price(self, url: str) -> float | None:
        """
        抓取商品价格。
        支持京东、淘宝商品页，演示常规提取逻辑。
        """
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)

            if "jd.com" in url:
                return self._parse_jd(resp.text)
            elif "taobao.com" in url or "tmall.com" in url:
                return self._parse_tb(resp.text)
            else:
                soup = BeautifulSoup(resp.text, "html.parser")
                price_selectors = [
                    ".price", ".current-price", ".sale-price",
                    '[data-price]', ".product-price", "#price"
                ]
                for sel in price_selectors:
                    elem = soup.select_one(sel)
                    if elem:
                        text = elem.get("data-price") or elem.get_text(strip=True)
                        return self._clean_price(text)

        except requests.RequestException as e:
            print(f"  [网络] {url[:40]}... → {e}")
        except Exception as e:
            print(f"  [解析] {url[:40]}... → {e}")
        return None

    def _parse_jd(self, html: str) -> float | None:
        """京东价格解析"""
        soup = BeautifulSoup(html, "html.parser")
        price_elem = soup.select_one(".price")
        if price_elem:
            text = price_elem.get_text(strip=True)
            return self._clean_price(text)
        return None

    def _parse_tb(self, html: str) -> float | None:
        """淘宝价格解析"""
        soup = BeautifulSoup(html, "html.parser")
        price_elem = soup.select_one(".tm-promo-price .tm-price")
        if price_elem:
            text = price_elem.get_text(strip=True)
            return self._clean_price(text)
        return None

    def _clean_price(self, text: str) -> float | None:
        """清洗价格字符串为浮点数"""
        import re
        nums = re.findall(r'\d+\.?\d*', text)
        if not nums:
            return None
        price = float(nums[0])
        if price > 0:
            return price
        return None

    def check_all(self) -> list:
        """检查所有商品价格，返回降价通知列表"""
        notifications = []
        print(f"\n{'='*50}")
        print(f"  价格监控巡检 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}\n")

        for p in self.products:
            print(f"  [{p['id']}] {p['name']}")
            price = self.fetch_price(p["url"])
            time.sleep(1 + random.random() * 2)  # 反爬延迟

            if price is None:
                p["status"] = "获取失败"
                print(f"      价格: 获取失败")
                continue

            p["current_price"] = price
            if p["lowest_price"] is None or price < p["lowest_price"]:
                p["lowest_price"] = price

            p["history"].append({
                "time": str(datetime.now()),
                "price": price
            })
            # 只保留最近 30 条记录
            p["history"] = p["history"][-30:]

            print(f"      当前: ¥{price:.2f}  |  目标: ¥{p['alert_price']:.2f}  |  最低: ¥{p['lowest_price']:.2f}")

            if price <= p["alert_price"]:
                p["status"] = f"已达标 (¥{price:.2f})"
                notifications.append(p)
                print(f"      >>> 价格已低于目标价！触发预警 <<<")
            else:
                p["status"] = "监控中"

        self._save_products()
        print(f"\n  共检查 {len(self.products)} 件商品\n")
        return notifications

    def send_alert(self, product: dict) -> bool:
        """发送降价邮件通知"""
        cfg = self.config
        if not cfg["sender"] or not cfg["password"]:
            print("  [邮件] 未配置发件人信息，跳过邮件通知")
            return False

        body = f"""
商品降价提醒！

商品: {product['name']}
当前价格: ¥{product['current_price']:.2f}
目标价格: ¥{product['alert_price']:.2f}
历史最低: ¥{product['lowest_price']:.2f}

立即查看: {product['url']}

---
电商价格监控系统 | github.com/chengnan12/price-monitor
"""
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = f"[降价提醒] {product['name']} 降至 ¥{product['current_price']:.2f}"
            msg["From"] = cfg["sender"]
            msg["To"] = cfg["receiver"] or cfg["sender"]

            with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=15) as server:
                server.starttls()
                server.login(cfg["sender"], cfg["password"])
                server.sendmail(cfg["sender"], [cfg["receiver"] or cfg["sender"]], msg.as_string())

            print(f"  [邮件] 已发送降价提醒 → {cfg['receiver'] or cfg['sender']}")
            return True
        except Exception as e:
            print(f"  [邮件] 发送失败: {e}")
            return False

    def list_products(self):
        """列出所有监控商品"""
        if not self.products:
            print("暂无监控商品，使用 add 命令添加。")
            return

        print(f"\n{'序号':<5} {'商品名称':<25} {'当前价':<10} {'目标价':<10} {'状态'}")
        print("-" * 70)
        for p in self.products:
            current = f"¥{p['current_price']:.2f}" if p['current_price'] else "未获取"
            print(f"{p['id']:<5} {p['name']:<25} {current:<10} ¥{p['alert_price']:<9.2f} {p['status']}")
        print()


def setup_config():
    """引导配置邮箱"""
    print("\n配置邮件通知（可选，用于降价时发送提醒）")
    print("支持 QQ邮箱 / 163邮箱，需开启 SMTP 并获取授权码\n")

    config = {
        "smtp_host": input("SMTP服务器 (默认 smtp.qq.com): ").strip() or "smtp.qq.com",
        "smtp_port": int(input("SMTP端口 (默认 587): ").strip() or 587),
        "sender": input("发件人邮箱: ").strip(),
        "password": input("邮箱授权码 (非登录密码): ").strip(),
        "receiver": input("收件人邮箱 (留空同发件人): ").strip(),
        "check_interval": 3600
    }

    CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n配置已保存 → {CONFIG_FILE}")


def main():
    monitor = PriceMonitor()

    if len(sys.argv) < 2:
        print("=" * 50)
        print("  电商价格监控系统")
        print("  github.com/chengnan12/price-monitor")
        print("=" * 50)
        print()
        print("命令:")
        print("  add    <名称> <URL> <目标价>  添加监控")
        print("  list                          查看列表")
        print("  check                         检查价格")
        print("  remove <编号>                 移除监控")
        print("  config                        邮件配置")
        print()
        print("示例:")
        print("  python monitor.py add 机械键盘 https://item.jd.com/xxx.html 299")
        return

    cmd = sys.argv[1].lower()

    if cmd == "add":
        if len(sys.argv) < 5:
            print("用法: monitor.py add <名称> <URL> <目标价>")
            return
        name = sys.argv[2]
        url = sys.argv[3]
        alert_price = float(sys.argv[4])
        pid = monitor.add(name, url, alert_price)
        print(f"已添加监控 [{pid}] {name} — 目标价 ¥{alert_price:.2f}")

    elif cmd == "list":
        monitor.list_products()

    elif cmd == "check":
        notifications = monitor.check_all()
        for p in notifications:
            monitor.send_alert(p)

    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("用法: monitor.py remove <编号>")
            return
        pid = int(sys.argv[2])
        if monitor.remove(pid):
            print(f"已移除监控 [{pid}]")
        else:
            print(f"未找到编号 [{pid}]")

    elif cmd == "config":
        setup_config()

    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
