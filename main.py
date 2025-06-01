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
seen_urls = set()
class StreamMonitor:
    def __init__(self):
        self.active_monitors = {}  # 存储活跃的监控 {url: driver}
        self.url_last_modified = 0  # url.txt 的最后修改时间
        self.running = True
        self.load_config()
        self.recording_status = {}  # 存储录制状态 {url: {"status": "recording/waiting", "start_time": timestamp}}
        
    def load_config(self):
        """加载配置文件"""
        try:
            if not os.path.exists('config.json'):
                self.config = {
                    "download_dir": "downloads",
                    "check_interval": 5
                }
                self.save_config()
            else:
                with open('config.json', 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
        except Exception as e:
            print(f"加载配置文件出错: {str(e)}")
            self.config = {
                "download_dir": "downloads",
                "check_interval": 5
            }
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件出错: {str(e)}")

    def set_download_dir(self, path):
        """设置下载目录"""
        self.config['download_dir'] = path
        self.save_config()
        # 确保目录存在
        if not os.path.exists(path):
            os.makedirs(path)
        print(f"下载目录已设置为: {path}")

    def read_urls(self):
        """读取url.txt中的URL列表"""
        try:
            with open('url.txt', 'r', encoding='utf-8') as f:
                urls = []
                for line in f:
                    url = line.strip()
                    if url:
                        # 分割 URL，只保留到直播间 ID 的部分
                        base_url = url.split('?')[0]  # 去掉查询参数
                        urls.append(base_url)
                return urls
        except Exception as e:
            print(f"读取url.txt出错: {str(e)}")
            return []

    def download_stream(self, stream_url, url):
        try:
            save_dir = self.config['download_dir']
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # 获取直播间ID作为文件名的一部分
            room_id = url.split('/')[-1]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'stream_{room_id}_{timestamp}.flv'
            filepath = os.path.join(save_dir, filename)
            
            print(f"\n开始下载流媒体文件: {filename}")
            print(f"保存到: {filepath}")
            print("下载中...")
            seen_urls.add(stream_url)
            self.recording_status[url] = {
                "status": "recording",
                "start_time": datetime.now(),
                "stream_url": stream_url,
                "room_id": room_id  # 添加房间ID到状态信息中
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': url,  # 添加直播间URL作为Referer
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(stream_url, headers=headers, stream=True)
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
            
            for log in logs:
                try:
                    log_data = json.loads(log['message'])['message']
                    if 'Network.requestWillBeSent' in log_data['method']:
                        request = log_data['params']
                        request_url = request.get('request', {}).get('url', '')
                        request_type = request.get('type', '')
                        
                        if (request_type.lower() == 'fetch' or 'fetch' in request_type.lower()) and 'stream' in request_url.lower() and 'pull-flv' in request_url.lower():
                            return request_url
                except:
                    continue
            
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
            


            
            while self.running and url in self.active_monitors:
                try:

                    driver.refresh()
                    time.sleep(2)
                    
                    stream_url = self.capture_stream_urls(driver, url)

                    if stream_url not in seen_urls and stream_url:
                        print(f"\n发现新的stream URL: {stream_url}")
                        print("准备下载...")
                        
                        if not self.download_stream(stream_url,url):
                            print("下载失败，将在下次检测时重试")
                            self.recording_status[url] = {"status": "waiting", "start_time": None}

                    else:
                        self.recording_status[url] = {"status": "waiting", "start_time": None}

                    time.sleep(5)  # 检查间隔
                    
                except Exception as e:
                    print(f"监控过程出错: {str(e)}")
                    self.recording_status[url] = {"status": "error", "start_time": None, "error": str(e)}
                    time.sleep(5)  # 出错后等待一段时间再继续
                    
        except Exception as e:
            print(f"创建监控出错: {str(e)}")
            if url in self.recording_status:
                self.recording_status[url] = {"status": "error", "start_time": None, "error": str(e)}

    def show_status(self):
        """显示所有直播间的状态"""
        print("\n=== 直播间状态 ===")
        
        # 检查是否有正在监控的直播间
        if not self.active_monitors and not self.recording_status:
            print("当前没有监控的直播间")
            return
        
        # 显示所有监控中的直播间状态
        for url in self.active_monitors.keys():
            print(f"\n直播间: {url}")
            if url in self.recording_status:
                status = self.recording_status[url]
                if status["status"] == "recording":
                    duration = datetime.now() - status["start_time"]
                    hours = duration.seconds // 3600
                    minutes = (duration.seconds % 3600) // 60
                    seconds = duration.seconds % 60
                    print(f"状态: 正在录制")
                    print(f"开始时间: {status['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"已录制时长: {hours}小时{minutes}分钟{seconds}秒")

                elif status["status"] == "waiting":
                    print("状态: 等待直播开始")
                elif status["status"] == "error":
                    print(f"状态: 发生错误 - {status.get('error', '未知错误')}")
            else:
                print("状态: 正在初始化监控...")

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
            
            # 启动状态显示线程
            def status_display_thread():
                # 给予初始化时间
                time.sleep(5)  # 等待5秒，让监控线程有时间初始化
                while self.running:
                    self.show_status()
                    time.sleep(30)  # 每30秒更新一次状态
            
            status_thread = threading.Thread(target=status_display_thread)
            status_thread.daemon = True
            status_thread.start()
            
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
