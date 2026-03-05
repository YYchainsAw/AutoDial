import subprocess
import time
import sys
import os
import socket
from datetime import datetime


class AutoDialer:
    def __init__(self, connection_name, username, password):
        self.connection_name = connection_name
        self.username = username
        self.password = password
        self.check_interval = 5
        self.reconnect_cooldown = 20
        self.last_connect_time = 0
        self.last_connect_success = True

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        try:
            with open("auto_dial.log", "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except:
            pass

    def check_internet_connection(self):
        """
        快速检查网络，任意一种成功即认为有网络
        总超时控制在5秒以内
        """
        # 方式1: TCP连接测试（超时2秒，最多试2个）
        tcp_targets = [
            ("114.114.114.114", 53),
            ("8.8.8.8", 53),
        ]

        for host, port in tcp_targets:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((host, port))
                sock.close()
                return True
            except:
                try:
                    sock.close()
                except:
                    pass
                continue

        # 方式2: DNS解析测试（超时2秒，最多试1个）
        try:
            socket.setdefaulttimeout(2)
            socket.getaddrinfo("www.baidu.com", 80)
            return True
        except:
            pass

        return False

    def is_connection_active(self):
        """检查宽带连接是否已激活"""
        try:
            result = subprocess.run(
                'rasdial',
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            output = result.stdout
            lines = output.split('\n')

            for i, line in enumerate(lines):
                if 'Connected' in line or '已连接' in line:
                    if i + 1 < len(lines) and self.connection_name in lines[i + 1]:
                        return True

            return False
        except:
            return False

    def dial_connection(self, force_disconnect=True):
        """执行拨号连接"""
        try:
            if not self.last_connect_success:
                current_time = time.time()
                time_since_last = current_time - self.last_connect_time
                if time_since_last < self.reconnect_cooldown:
                    wait_time = int(self.reconnect_cooldown - time_since_last)
                    self.log(f"⏱ 冷却中，还需等待 {wait_time} 秒...")
                    return False

            self.log(f"🔄 尝试连接到 '{self.connection_name}'...")

            if force_disconnect:
                subprocess.run(
                    f'rasdial "{self.connection_name}" /DISCONNECT',
                    shell=True, capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                time.sleep(2)

            result = subprocess.run(
                f'rasdial "{self.connection_name}" {self.username} {self.password}',
                shell=True, capture_output=True, text=True,
                encoding='utf-8', errors='ignore', timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            self.last_connect_time = time.time()

            if result.returncode == 0 or 'successfully' in result.stdout.lower():
                self.log("✓ 拨号成功")
                time.sleep(5)
                self.last_connect_success = True
                return True
            else:
                error_msg = (result.stderr or result.stdout)[:200]
                self.log(f"✗ 连接失败: {error_msg}")
                self.last_connect_success = False
                return False

        except subprocess.TimeoutExpired:
            self.log("✗ 连接超时")
            self.last_connect_time = time.time()
            self.last_connect_success = False
            return False
        except Exception as e:
            self.log(f"✗ 拨号出错: {e}")
            self.last_connect_success = False
            return False

    def confirm_network_down(self):
        """
        严格确认网络是否真的断了
        连续3次检测全部失败才认为断网，间隔2秒
        """
        for i in range(3):
            if self.check_internet_connection():
                return False

            self.log(f"   确认检测 {i + 1}/3 失败")

            if i < 2:
                time.sleep(2)

        return True

    def run(self):
        """运行自动拨号监控"""
        self.log("=" * 60)
        self.log("🚀 自动拨号程序启动 (v3.2 快速版)")
        self.log(f"📡 连接名称: {self.connection_name}")
        self.log(f"👤 用户名: {self.username}")
        self.log(f"⏱ 检查间隔: {self.check_interval}秒")
        self.log("=" * 60)

        # 启动时检查
        self.log("📊 检查初始状态...")
        is_active = self.is_connection_active()
        has_internet = self.check_internet_connection()
        self.log(f"初始: 连接{'已激活' if is_active else '未激活'}, 网络{'可用' if has_internet else '不可用'}")

        if is_active and has_internet:
            self.log("✅ 网络正常，进入监控模式")
        elif not is_active:
            self.log("⚠ 连接未激活，将尝试建立连接")

        self.log("=" * 60)

        consecutive_failures = 0
        max_consecutive_failures = 3
        check_count = 0
        last_log_minute = -1

        while True:
            try:
                check_count += 1
                current_minute = check_count * self.check_interval // 60

                is_active = self.is_connection_active()
                has_internet = self.check_internet_connection()

                # ========== 网络正常 ==========
                if has_internet:
                    if consecutive_failures > 0:
                        self.log("✅ 网络已恢复")
                        consecutive_failures = 0
                    elif current_minute > 0 and current_minute % 10 == 0 and current_minute != last_log_minute:
                        self.log(f"✅ 网络正常 (已运行 {current_minute} 分钟)")
                        last_log_minute = current_minute

                    time.sleep(self.check_interval)
                    continue

                # ========== 快速检查失败，严格确认 ==========
                self.log("⚠ 网络异常，严格确认中...")

                if not self.confirm_network_down():
                    self.log("✅ 确认通过，网络正常（临时波动）")
                    time.sleep(self.check_interval)
                    continue

                # ========== 确认断网，重连 ==========
                self.log("=" * 60)
                is_active = self.is_connection_active()
                self.log(f"❌ 确认断网! (连接{'激活' if is_active else '未激活'})")

                if self.dial_connection(force_disconnect=is_active):
                    consecutive_failures = 0
                    self.log("⏳ 等待连接稳定...")
                    time.sleep(8)

                    if self.check_internet_connection():
                        self.log("✅ 网络已成功恢复!")
                    else:
                        self.log("⚠ 拨号成功但网络验证失败，继续监控...")
                        consecutive_failures += 1
                else:
                    consecutive_failures += 1
                    self.log(f"✗ 连接失败 ({consecutive_failures}/{max_consecutive_failures})")

                    if consecutive_failures >= max_consecutive_failures:
                        self.log(f"⚠ 连续失败{max_consecutive_failures}次，等待2分钟...")
                        time.sleep(120)
                        consecutive_failures = 0
                        self.last_connect_success = True

                self.log("=" * 60)
                time.sleep(10 if consecutive_failures > 0 else self.check_interval)

            except KeyboardInterrupt:
                self.log("\n👋 程序已停止")
                sys.exit(0)
            except Exception as e:
                self.log(f"❌ 运行时错误: {e}")
                time.sleep(self.check_interval)


def main():
    try:
        is_admin = os.system("net session >nul 2>&1") == 0
        if not is_admin:
            print("⚠ 建议以管理员权限运行")
            print()
    except:
        pass

    CONNECTION_NAME = "Netkeeper"
    USERNAME = "202426704040@jxsd"
    PASSWORD = "704040"

    dialer = AutoDialer(CONNECTION_NAME, USERNAME, PASSWORD)
    dialer.run()


if __name__ == "__main__":
    main()