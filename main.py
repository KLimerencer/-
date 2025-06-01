from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import requests
import os
from datetime import datetime
import threading
import sys
import logging

# 禁用不必要的日志
logging.getLogger('selenium').setLevel(logging.ERROR)
os.environ['WDM_LOG_LEVEL'] = '0'

class StreamMonitor:
    def __init__(self):
        self.active_monitors = {}  # 存储活跃的监控 {url: driver}
        self.url_last_modified = 0  # url.txt 的最后修改时间
        self.running = True
        
    def read_urls(self):
        """读取url.txt中的URL列表"""
        try:
            with open('url.txt', 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"读取url.txt出错: {str(e)}")
            return []

    def download_stream(self, url, save_dir='downloads'):
        try:
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'stream_{timestamp}.flv'
            filepath = os.path.join(save_dir, filename)
            
            print(f"\n开始下载流媒体文件: {filename}")
            print("下载中...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://live.douyin.com/',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
            
        except Exception as e:
            print(f"\n下载出错: {str(e)}")
            return False

    def capture_stream_urls(self, driver, url):
        try:
            logs = driver.get_log('performance')
            stream_urls = set()
            
            for log in logs:
                try:
                    log_data = json.loads(log['message'])['message']
                    if 'Network.requestWillBeSent' in log_data['method']:
                        request = log_data['params']
                        request_url = request.get('request', {}).get('url', '')
                        request_type = request.get('type', '')
                        
                        if (request_type.lower() == 'fetch' or 'fetch' in request_type.lower()) and 'stream' in request_url.lower():
                            if request_url.endswith('.flv') or 'stream-' in request_url:
                                stream_urls.add(request_url)
                except:
                    continue
            return stream_urls
            
        except Exception as e:
            print(f"捕获流媒体URL出错: {str(e)}")
            return set()

    def create_chrome_driver(self):
        """创建配置好的Chrome驱动"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')  # 使用新版无界面模式
        options.add_argument('--disable-gpu')  # 禁用GPU加速
        options.add_argument('--log-level=3')  # 只显示重要日志
        options.add_argument('--silent')  # 静默模式
        options.add_argument('--disable-web-security')  # 禁用网页安全性检查
        options.add_argument('--disable-webgl')  # 禁用WebGL
        options.add_argument('--disable-software-rasterizer')  # 禁用软件光栅化
        options.add_argument('--disable-dev-shm-usage')  # 禁用/dev/shm使用
        options.add_argument('--no-sandbox')  # 禁用沙盒
        options.add_argument('--ignore-certificate-errors')  # 忽略证书错误
        options.add_argument('--disable-extensions')  # 禁用扩展
        options.add_argument('--disable-notifications')  # 禁用通知
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        # 添加性能优化参数
        prefs = {
            'profile.default_content_setting_values': {
                'images': 2,  # 不加载图片
                'javascript': 1,  # 允许JavaScript
                'notifications': 2,  # 禁用通知
                'plugins': 2  # 禁用插件
            }
        }
        options.add_experimental_option('prefs', prefs)
        
        service = webdriver.chrome.service.Service(
            log_output=os.devnull  # 将服务日志重定向到空
        )
        
        return webdriver.Chrome(options=options, service=service)

    def monitor_url(self, url):
        """监控单个URL的线程函数"""
        try:
            print(f"\n开始监控页面: {url}")
            
            driver = self.create_chrome_driver()
            self.active_monitors[url] = driver
            driver.get(url)
            
            seen_urls = set()
            
            while self.running and url in self.active_monitors:
                try:
                    print(f"\n检查页面新的流媒体链接: {url}")
                    driver.refresh()
                    time.sleep(2)
                    
                    new_urls = self.capture_stream_urls(driver, url)
                    
                    for stream_url in new_urls:
                        if stream_url not in seen_urls:
                            print(f"\n发现新的stream URL: {stream_url}")
                            print("准备下载...")
                            
                            if self.download_stream(stream_url):
                                print("下载成功！")
                                seen_urls.add(stream_url)
                            else:
                                print("下载失败，将在下次检测时重试")
                    
                    time.sleep(5)  # 检查间隔
                    
                except Exception as e:
                    print(f"监控过程出错: {str(e)}")
                    time.sleep(5)  # 出错后等待一段时间再继续
                    
        except Exception as e:
            print(f"创建监控出错: {str(e)}")

    def check_url_updates(self):
        """检查url.txt更新的线程函数"""
        while self.running:
            try:
                current_modified = os.path.getmtime('url.txt')
                if current_modified > self.url_last_modified:
                    print("\n检测到url.txt有更新，正在处理新的URL...")
                    self.url_last_modified = current_modified
                    
                    current_urls = set(self.read_urls())
                    monitored_urls = set(self.active_monitors.keys())
                    
                    new_urls = current_urls - monitored_urls
                    for url in new_urls:
                        print(f"\n发现新的直播间地址: {url}")
                        thread = threading.Thread(target=self.monitor_url, args=(url,))
                        thread.daemon = True
                        thread.start()
                
                time.sleep(5)  # 检查url.txt的间隔
                
            except Exception as e:
                print(f"检查URL更新出错: {str(e)}")
                time.sleep(5)

    def start(self):
        """启动监控"""
        try:
            # 设置Ctrl+C处理
            def signal_handler(sig, frame):
                print("\n正在退出程序...")
                os._exit(0)  # 直接退出程序
            
            import signal
            signal.signal(signal.SIGINT, signal_handler)
            
            # 记录初始的文件修改时间
            self.url_last_modified = os.path.getmtime('url.txt')
            
            # 启动URL更新检查线程
            update_thread = threading.Thread(target=self.check_url_updates)
            update_thread.daemon = True
            update_thread.start()
            
            # 启动初始URL的监控
            initial_urls = self.read_urls()
            for url in initial_urls:
                thread = threading.Thread(target=self.monitor_url, args=(url,))
                thread.daemon = True
                thread.start()
            
            # 保持主线程运行
            while True:
                time.sleep(1)
                
        except Exception as e:
            print(f"启动监控出错: {str(e)}")
            sys.exit(1)

def main():
    monitor = StreamMonitor()
    monitor.start()

if __name__ == "__main__":
    main()
