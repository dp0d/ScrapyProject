# -- coding: utf-8 --
import time
import threading
import requests

from scrapy import signals

# 提取代理IP的api
api_url = 'https://dps.kdlapi.com/api/getdps/?orderid=965208072230596&num=10&signature=bqcsohuyc0qcmz1446bn3jt234sbcezq&pt=1&format=json&sep=1'
foo = True

class Proxy:

    def __init__(self, ):
        self.api_url = api_url
        self.username = 'xxx'
        self.password = 'xxx'
        self._proxy_list = self.get_proxy_lis()

    def get_proxy_lis(self):

        print(
            "-------------------------------------------------从代理商获取IP代理池--------------------------------------------------")
        proxy_lis = requests.get(self.api_url).json().get('data').get('proxy_list')
        # print(
        #     "-------------------------------------------------获取成功，开始测试IP代理池--------------------------------------------------")
        #
        # # 测试连通性
        # proxy_lis = [proxy for proxy in proxy_lis if self.verification(proxy)]
        #
        # # 可用代理列表长度为零则重新获取
        # while not len(proxy_lis):
        #     print(
        #         "-------------------------------------------------可用IP代理获取失败，重新获取中------------\
        #         --------------------------------------")
        #     proxy_lis = requests.get(self.api_url).json().get('data').get('proxy_list')
        #     print(
        #         "-------------------------------------------------开始测试新获IP代理池--------------------------------------------------")
        #
        #     # 测试连通性
        #     proxy_lis = [proxy for proxy in proxy_lis if self.verification(proxy)]
        print(
            "-------------------------------------------------成功获得可用IP代理池（大小为%d）如下--------------------------------------------------" % len(proxy_lis))
        print(proxy_lis)
        self.index_ = 1

        return proxy_lis

    def get_next_proxy(self):
        self.index_ += 1
        proxy = self._proxy_list[self.index_ % len(self._proxy_list)]
        return proxy

    @property
    def proxy_list(self):
        return self._proxy_list

    @proxy_list.setter
    def proxy_list(self, list):
        self._proxy_list = list

    # 测试IP代理是否正常响应
    def verification(self, proxy):
        head = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
            'Connection': 'keep-alive'}
        '''http://icanhazip.com会返回当前的IP地址'''

        proxies = {
            "http": "http://%(user)s:%(pwd)s@%(proxy)s/" % {"user": self.username, "pwd": self.password, "proxy": proxy},
            "https": "http://%(user)s:%(pwd)s@%(proxy)s/" % {"user": self.username, "pwd": self.password, "proxy": proxy}
        }
        try:
            p = requests.get('http://icanhazip.com', headers=head, proxies=proxies, timeout=2)
            if p.status_code == 200:
                return True
            return False
        except:
            return False


pro = Proxy()
print(pro.proxy_list)


class MyExtend:

    def __init__(self, crawler):
        self.crawler = crawler
        # 将自定义方法绑定到scrapy信号上,使程序与spider引擎同步启动与关闭
        # scrapy信号文档: https://www.osgeo.cn/scrapy/topics/signals.html
        # scrapy自定义拓展文档: https://www.osgeo.cn/scrapy/topics/extensions.html
        crawler.signals.connect(self.start, signals.engine_started)
        crawler.signals.connect(self.close, signals.spider_closed)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def start(self):
        t = threading.Thread(target=self.extract_proxy)
        t.start()

    def extract_proxy(self):
        while foo:
            # 设置每120秒提取一次ip
            time.sleep(60)
            pro.proxy_list = pro.get_proxy_lis()

    def close(self):
        global foo
        foo = False