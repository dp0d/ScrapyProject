# -*- coding: utf-8 -*-
# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# from .myextend import pro
import scrapy
from w3lib.http import basic_auth_header

import random
from twisted.internet import defer
from twisted.internet.error import TimeoutError, DNSLookupError, \
    ConnectionRefusedError, ConnectionDone, ConnectError, \
    ConnectionLost, TCPTimedOutError
from scrapy.http import HtmlResponse
from twisted.web.client import ResponseFailed
from scrapy.core.downloader.handlers.http11 import TunnelError
from scrapy_fang.tools import GetRandomUserAgent
from scrapy.downloadermiddlewares.retry import RetryMiddleware

from scrapy import signals
from w3lib.http import basic_auth_header


class UserAgentMiddleware(object):
    get_head = GetRandomUserAgent()

    def process_request(self, request, spider):
        UserAgent = self.get_head.agent_head()['User-Agent']
        request.headers["User-Agent"] = UserAgent


# 重定向
class RedirectionMiddleware(object):
    head = GetRandomUserAgent()
    User_Agent = head.agent_head()

    # 处理URL重定向问题
    def process_response(self, request, response, spider):
        # 从response的body中提取重定向的网址
        redirected_url = response.xpath("//a[@class='btn-redir']//@href").get()
        # 如果抓取成功，则说明进行了重定向，返回新的请求
        if redirected_url:
            return scrapy.Request(url=str(redirected_url), headers=self.User_Agent)

        # 否则返回原response
        return response


# 隧道代理
class TUNProxyDownloaderMiddleware:

    def process_request(self, request, spider):
        proxy = "tps553.kdlapi.com:15818"
        request.meta['proxy'] = "http://%(proxy)s" % {'proxy': proxy}
        # 用户名密码认证
        request.headers['Proxy-Authorization'] = basic_auth_header('t15209935663171', 'obs96q91')  # 白名单认证可注释此行
        request.headers["Connection"] = "close"
        # print('使用代理', request.meta['proxy'], '*' * 200)
        return None


# TUN模式更换代理
class My_RetryMiddleware(RetryMiddleware):
    get_head = GetRandomUserAgent()
    def process_exception(self, request, exception, spider):
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY):
            proxy = "tps553.kdlapi.com:15818"
            request.meta['proxy'] = "http://%(proxy)s" % {'proxy': proxy}
            # 用户名密码认证
            request.headers['Proxy-Authorization'] = basic_auth_header('t15209935663171', 'obs96q91')  # 白名单认证可注释此行
            request.headers["Connection"] = "close"

            UserAgent = self.get_head.agent_head()['User-Agent']
            request.headers["User-Agent"] = UserAgent
            print("出现异常%s，触发自定义重试中间件，更换ip代理" % exception, "*" * 200)

            return self._retry(request, exception, spider)


class ProcessAllExceptionMiddleware(object):
    ALL_EXCEPTIONS = (defer.TimeoutError, TimeoutError, DNSLookupError,
                      ConnectionRefusedError, ConnectionDone, ConnectError,
                      ConnectionLost, TCPTimedOutError, ResponseFailed,
                      IOError, TunnelError)

    def process_response(self, request, response, spider):
        # 捕获状态码为40x/50x的response
        if str(response.status).startswith('4') or str(response.status).startswith('5'):
            # 随意封装，直接返回response，spider代码中根据url==''来处理response
            response = HtmlResponse(url='')
            return response
        # 其他状态码不处理
        return response

    def process_exception(self, request, exception, spider):

        # 捕获几乎所有的异常
        if isinstance(exception, self.ALL_EXCEPTIONS):
            # 在日志中打印异常类型
            print('捕获异常: %s' % (exception))
            # 随意封装一个response，返回给spider
            response = HtmlResponse(url='exception')
            return response
        # 打印出未捕获到的异常
        print('未捕获到的异常: %s' % exception)
