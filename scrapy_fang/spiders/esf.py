import time
import pandas as pd
import scrapy
import re
from scrapy_fang.items import UrlItem, EsfItem, EsfInfoItem
from scrapy.http import HtmlResponse
import random, requests
from scrapy_fang.tools import DealCaptcha, GetRandomUserAgent
from lxml import etree
from urllib.parse import urljoin


class EsfSpider(scrapy.Spider):
    # 别名，后续用来其启动爬虫
    name = 'esf'
    # 允许爬取的页面
    allowed_domains = ['fang.com']
    # 启动爬取的页面
    start_urls = ['https://www.fang.com/SoufunFamily.htm']
    # start_urls = ['https://hz.esf.fang.com/chushou/3_261726225.htm?rfss=1-9cbca046022595aa48-37']
    # start_urls = ['https://hz.esf.fang.com/chushou/3_261726225.htm']

    get_random_UserAgent = GetRandomUserAgent()

    def get_redirected_url(self, url):
        head = self.get_random_UserAgent.agent_head()
        # 构造scrapy的response对象。
        req_response = requests.get(url, headers=head)
        response = HtmlResponse(url=url, body=req_response.content)

        # 处理重定向
        redirected_url = response.xpath("//a[@class='btn-redir']//@href").get()

        # 如果抓取成功，则说明进行了重定向，发送一个新的请求而不是将得到的响应发给爬虫程序
        if redirected_url:
            print("重定向", redirected_url, "*" * 200)
            return redirected_url
        return url

    # Scrapy框架默认调用这个方法。response.body是html源码
    def parse(self, response):
        df = pd.read_csv('esf_info.csv')
        esfhousenews_urls = df[['esfhousenews_url']].values
        provinces = df[['province']].values
        cities = df[['city']].values
        k = 1
        for u, p, c in zip(esfhousenews_urls, provinces, cities):
            if k > 5:
                break
            esfhousenews_url = u[0]
            province = p[0]
            city = c[0]
            try:
                directed_url = self.get_redirected_url(esfhousenews_url)
                yield scrapy.Request(url=directed_url, callback=self.parse_esfhouseInfo,
                                 meta={"info": (province, city, directed_url)}, dont_filter=True)
            except Exception as ex:
                print("捕获异常%s" % ex)

    # 对于二手房详情页面的解析
    def parse_esfhouseInfo(self, response):
        province, city, esf_link = response.meta.get("info")
        print(
            "-------------------------------------------------对于%s二手房 %s 详情页的解析--------------------------------------------------" % (
                province + ' ' + city, esf_link))

        # 验证码
        response_url = str(response.url)
        print(response)

        house_info_divs = response.xpath(
            "//div[contains(@class, 'tr-line clearfix')]//div[contains(@class,'trl-item1')]")

        if 'captcha' in response_url and not house_info_divs:
            with open('captcha.txt', 'a', encoding='utf-8') as f:
                f.write(response_url + '\n')
            print('处理验证码', '*' * 200)
            deal_captcha = DealCaptcha(parse_target='EsfInfoItem', url=response_url)
            item = deal_captcha.run()
            if item:
                item['province'] = province
                item['city'] = city
                item['esf_link'] = esf_link
                return item
        elif house_info_divs:
            print('链接解析成功了', '*' * 200)
            item = EsfInfoItem()
            item['province'] = province
            item['city'] = city
            item['esf_link'] = esf_link

            title = response.xpath("//span[@class='tit_text']//text()").get()
            if title:
                item['title'] = title.strip()
            if len(house_info_divs) == 6:
                # 户型
                room_type = house_info_divs[0].xpath(".//div[@class='tt']//text()").get()
                if room_type:
                    item['room_type'] = room_type.strip()
                # 面积
                area = house_info_divs[1].xpath(".//div[@class='tt']//text()").get()
                if area:
                    item['area'] = area.strip()
                # 单价
                unit_price = house_info_divs[2].xpath(".//div[@class='tt']//text()").get()
                if unit_price:
                    item['unit_price'] = unit_price.strip()
                # 朝向
                orientation = house_info_divs[3].xpath(".//div[@class='tt']//text()").get()
                if orientation:
                    item['orientation'] = orientation.strip()
                # 楼层
                floor_info = house_info_divs[4].xpath(".//div[@class='tt']//text()").get()
                floor_info_a = house_info_divs[4].xpath(".//div[@class='tt']//a//text()").get()
                floor_type = house_info_divs[4].xpath(".//div[@class='font14']//text()").get()
                if floor_info_a and floor_type:
                    item['floor'] = floor_info_a.strip() + ',' + floor_type.strip()
                elif floor_info and floor_type:
                    item['floor'] = floor_info.strip() + ',' + floor_type.strip()
                # 装修
                decoration = house_info_divs[5].xpath(".//div[@class='tt']//text()").get()
                decoration_a = house_info_divs[5].xpath(".//div[@class='tt']/a//text()").get()
                if decoration_a:
                    item['decoration'] = decoration_a.strip()
                elif decoration:
                    item['decoration'] = decoration.strip()

            # 总价
            total_price = response.xpath("//div[contains(@class, 'price_esf')]/i//text()").get()
            if total_price:
                item['total_price'] = total_price.strip() + '万元'
            # 房源信息
            xpath_house_info_lis = response.xpath(
                "//div[contains(@class, 'content-item fydes-item')]//div[contains(@class, 'cont clearfix')]//div")
            for div in xpath_house_info_lis:
                if len(div.xpath(".//span//text()")) == 2:
                    # 建筑年代
                    if div.xpath(".//span//text()")[0].get().strip() == '建筑年代':
                        build_year = div.xpath(".//span//text()")[1].get()
                        item['build_year'] = build_year.strip()
            # 小区
            community = response.xpath("//a[@id='kesfsfbxq_A01_01_05']//text()").get()
            if community:
                item['community'] = community
            # 小区信息
            xpath_community_info_lis = response.xpath("//div[contains(@class, 'cont pt30')]")
            # 小区信息顶栏
            for div in xpath_community_info_lis.xpath(".//div[contains(@class, 'topt clearfix')]//div"):
                # 小区参考均价
                if div.xpath(".//span//text()")[0].get().strip() == '参考均价':
                    community_price = div.xpath(".//span")[1].xpath(".//i//text()").get()
                    if community_price:
                        item['community_price'] = community_price.strip() + ' 元/平米'

                # 小区均价同比去年
                if div.xpath(".//span//text()")[0].get().strip() == '同比去年':
                    community_price_to_last_year = div.xpath(".//span")[1].xpath(".//em//span//text()").get()
                    if community_price_to_last_year:
                        item['community_price_to_last_year'] = community_price_to_last_year.strip()
                # 小区均价环比上月
                if div.xpath(".//span//text()")[0].get().strip() == '环比上月':
                    community_price_to_last_month = div.xpath(".//span")[1].xpath(".//em//span//text()").get()
                    if community_price_to_last_month:
                        item['community_price_to_last_month'] = community_price_to_last_month.strip()
            for div in xpath_community_info_lis.xpath(".//div[@class='clearfix']//div"):
                if len(div.xpath(".//span")) == 2:
                    # 绿化率
                    if '绿' in div.xpath(".//span//text()")[0].get().strip():
                        plant_rate = div.xpath(".//span//text()")[1].get()
                        if plant_rate:
                            item['plant_rate'] = plant_rate.strip()
                    # 小区容积率
                    if '容' in div.xpath(".//span//text()")[0].get().strip():
                        community_volume_rate = div.xpath(".//span//text()")[1].get()
                        if community_volume_rate:
                            item['community_volume_rate'] = community_volume_rate.strip()
                    # 小区总户数
                    if '户' in div.xpath(".//span//text()")[0].get().strip():
                        community_total_family_num = div.xpath(".//span//text()")[1].get()
                        if community_total_family_num:
                            item['community_total_family_num'] = community_total_family_num.strip()
                    # 产权年限
                    if div.xpath(".//span//text()")[0].get().strip() == '产权年限':
                        property_tenure = div.xpath(".//span//text()")[1].get()
                        if property_tenure:
                            item['property_tenure'] = property_tenure.strip() + '年'
                    # 小区总楼栋数
                    if div.xpath(".//span//text()")[0].get().strip() == '总楼栋数':
                        community_total_building_num = div.xpath(".//span//text()")[1].get()
                        if community_total_building_num:
                            item['community_total_building_num'] = community_total_building_num.strip()
                    # 小区物业费用
                    if div.xpath(".//span//text()")[0].get().strip() == '物业费用':
                        community_property_expenses = div.xpath(".//span//text()")[1].get()
                        if community_property_expenses:
                            item['community_property_expenses'] = community_property_expenses.strip()
                    # 小区人车分流
                    if div.xpath(".//span//text()")[0].get().strip() == '人车分流':
                        community_people_vehicles_depart = div.xpath(".//span//text()")[1].get()
                        if community_people_vehicles_depart:
                            item['community_people_vehicles_depart'] = community_people_vehicles_depart.strip()
            return item
