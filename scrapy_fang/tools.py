
from lxml import etree

import re

from selenium import webdriver


from selenium.webdriver import ActionChains

import requests
import cv2
import hashlib

import json

from scrapy_fang.items import EsfItem, EsfInfoItem
from selenium.webdriver.common.by import By

import random
import time


class DealCaptcha(object):
    def __init__(self, parse_target, url):
        self.dir_path = '/home/oliver/PycharmProjects/scrapy_fang/img/'
        # 得到随机请求头
        us_head_obj = GetRandomUserAgent()
        us_head = us_head_obj.agent_head()['User-Agent']

        self.options = webdriver.ChromeOptions()
        # 赋值请求头
        self.options.add_argument(us_head)

        # 无界面模式
        self.options.add_argument('--headless')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')

        self.url = str(url)
        self.parse_target = parse_target
        self.bg_jpg_path = self.dir_path + hashlib.md5(
            (str(time.time()) + self.url).encode("UTF-8")).hexdigest() + 'bg.jpg'
        self.block_png_path = self.dir_path + hashlib.md5(
            (str(time.time()) + self.url).encode("UTF-8")).hexdigest() + 'block.png'
        self.driver = webdriver.Chrome(chrome_options=self.options,
                                       executable_path='/usr/local/driver/chromedriver', )  # desired_capabilities=caps)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                })
            """
        })
        # 设置超时
        self.driver.set_page_load_timeout(20)
        self.driver.set_script_timeout(20)  # 这两种设置都进行才有效

    def get_captcha(self):
        # 背景图片
        bg = self.driver.find_element(by=By.CLASS_NAME, value="img-bg").get_attribute('src')
        with open(self.bg_jpg_path, mode='wb') as f:
            f.write(requests.get(bg).content)
        # 滑动图片
        block = self.driver.find_element(by=By.CLASS_NAME, value='img-block').get_attribute('src')
        with open(self.block_png_path, mode='wb') as f:
            f.write(requests.get(block).content)

        image = cv2.imread(self.block_png_path, cv2.IMREAD_UNCHANGED)  # 读取图片
        # cv2.imshow('1', image)
        # 保存裁剪后图片
        box = self.get_transparency_location(image)
        result = self.cv2_crop(image, box)
        cv2.imwrite(self.block_png_path, result)

    def cv2_crop(self, im, box):
        '''cv2实现类似PIL的裁剪

        :param im: cv2加载好的图像
        :param box: 裁剪的矩形，(left, upper, right, lower)元组
        '''
        return im.copy()[box[1]:box[3], box[0]:box[2], :]

    def get_transparency_location(self, image):
        '''获取基于透明元素裁切图片的左上角、右下角坐标

        :param image: cv2加载好的图像
        :return: (left, upper, right, lower)元组
        '''
        # 1. 扫描获得最左边透明点和最右边透明点坐标
        height, width, channel = image.shape  # 高、宽、通道数
        assert channel == 4  # 无透明通道报错
        first_location = None  # 最先遇到的透明点
        last_location = None  # 最后遇到的透明点
        first_transparency = []  # 从左往右最先遇到的透明点，元素个数小于等于图像高度
        last_transparency = []  # 从左往右最后遇到的透明点，元素个数小于等于图像高度
        for y, rows in enumerate(image):
            for x, BGRA in enumerate(rows):
                alpha = BGRA[3]
                if alpha != 0:
                    if not first_location or first_location[1] != y:  # 透明点未赋值或为同一列
                        first_location = (x, y)  # 更新最先遇到的透明点
                        first_transparency.append(first_location)
                    last_location = (x, y)  # 更新最后遇到的透明点
            if last_location:
                last_transparency.append(last_location)

        # 2. 矩形四个边的中点
        top = first_transparency[0]
        bottom = first_transparency[-1]
        left = None
        right = None
        for first, last in zip(first_transparency, last_transparency):
            if not left:
                left = first
            if not right:
                right = last
            if first[0] < left[0]:
                left = first
            if last[0] > right[0]:
                right = last

        # 3. 左上角、右下角
        upper_left = (left[0], top[1])  # 左上角
        bottom_right = (right[0], bottom[1])  # 右下角

        return upper_left[0], upper_left[1], bottom_right[0], bottom_right[1]

    def template_matching(self, bg, block):
        # 读取目标图片
        target = cv2.imread(bg)
        # 读取模板图片
        template = cv2.imread(block)
        # 获得模板图片的高宽尺寸
        theight, twidth = template.shape[:2]
        # 执行模板匹配，采用的匹配方式cv2.TM_SQDIFF_NORMED
        result = cv2.matchTemplate(target, template, cv2.TM_SQDIFF_NORMED)

        # 归一化处理
        cv2.normalize(result, result, 0, 1, cv2.NORM_MINMAX, -1)
        # 寻找矩阵（一维数组当做向量，用Mat定义）中的最大值和最小值的匹配结果及其位置
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        return min_loc[0], min_loc[1]

    def get_track(self, distance):
        """
        根据偏移量获取移动轨迹
        :param distance: 偏移量
        :return: 移动轨迹
        相关公式：
        x = x0 * t + 0.5 * a * t * t
        v = v0 + a * t
        """
        v = 0  # 初速度
        t = 2  # 单位时间为0.2s来统计轨迹，轨迹即0.2内的位移
        tracks = []  # 位移/轨迹列表，列表内的一个元素代表0.2s的位移
        current = 0  # 当前的位移
        mid = distance * 1 / 2  # 到达mid值开始减速
        distance += 20  # 先滑过一点，最后再反着滑动回来

        while current < distance:
            if current < mid:
                # 加速度越小，单位时间的位移越小,模拟的轨迹就越多越详细
                a = 0.1  # 加速运动
            else:
                a = -0.1  # 减速运动
            v0 = v  # 初速度
            s = v0 * t + 0.5 * a * (t ** 2)  # 0.2秒时间内的位移
            current += s  # 当前的位置
            tracks.append(round(s))  # 添加到轨迹列表
            # 实现停顿
            tracks.append(0)
            v = 0.2
            # v = v0 + a * t  # 速度已经达到v,该速度作为下次的初速度

        # 反着滑动到大概准确位置
        for i in range(3):
            tracks.append(-2)
        for i in range(4):
            tracks.append(-1)
        # print(tracks)
        return tracks

    def move_to_gap(self, tracks):
        # 移动滑块
        drop = self.driver.find_element(by=By.CLASS_NAME, value="verifyicon")
        ActionChains(self.driver).click_and_hold(drop).perform()
        for x in tracks:
            yoffset_random = random.uniform(-2, 4)
            ActionChains(self.driver).move_by_offset(xoffset=x, yoffset=yoffset_random).perform()
        time.sleep(1)
        ActionChains(self.driver).release().perform()

    def run(self):
        try:
            self.driver.get(self.url)
            # 隐式等待
            self.driver.implicitly_wait(10)
            time.sleep(3)
            verification_code = self.driver.find_element(by=By.CSS_SELECTOR, value='.info p').text
            if verification_code == "请拖动滑块进行验证：":
                sucess = self.driver.find_element(by=By.CSS_SELECTOR, value='.drag-text').text
                # print(sucess, '*'*200)
                # 下载验证码
                # 识别次数大于3次换页
                locate_time = 0
                while sucess != '验证通过啦！' and locate_time < 3:
                    self.get_captcha()
                    x, y = self.template_matching(self.bg_jpg_path, self.block_png_path)
                    self.move_to_gap([x])
                    print(x, y, self.url, '*' * 200)
                    time.sleep(2)
                    sucess = self.driver.find_element(by=By.CSS_SELECTOR, value='.drag-text').text

                    # 定位次数+1
                    locate_time += 1
                    print("验证码循环1，-第%d次" % locate_time, '*' * 200)
                    print(sucess, '*' * 200)
                self.driver.find_element(by=By.ID, value="captcha_submit_btn").click()
                time.sleep(1)
                Html_document = self.driver.execute_script("return document.documentElement.outerHTML")
                self.driver.close()
                if self.parse_target == 'page_num':
                    return self.parse_page_num(Html_document)
                elif self.parse_target == 'EsfItem':
                    # print(self.parse_lis_page(Html_document))
                    return self.parse_lis_page(Html_document)
                elif self.parse_target == 'EsfInfoItem':
                    # print(self.parse_info_page(Html_document))
                    return self.parse_info_page(Html_document)
                else:
                    return None
            # 刷新页面得到新图
            print('验证码处理超3次退出！', '*' * 200)
            self.driver.close()
            return None
        except Exception as ex:
            print('验证码处理异常！%s' % ex, '*' * 200)
            # 尝试关闭driver
            try:
                self.driver.close()
                return None
            except:
                return None

    def parse_page_num(self, Html_document):
        xml_obj = etree.HTML(Html_document)
        page_num_text = xml_obj.xpath("//div[@class='page_al']/span/text()")
        if len(page_num_text):
            # 将不是数字的替换为空
            page_num_text = page_num_text[-1]
            page_num = re.sub('\D', '', page_num_text)
            page_num = page_num
        else:
            page_num = '1'
        return page_num

    def parse_lis_page(self, Html_document):
        if type(Html_document) == str:
            xml_obj = etree.HTML(Html_document)
        else:
            xml_obj = etree.HTML('NoneType')
        dls = xml_obj.xpath("//dl[@class='clearfix']")
        item_lis = []
        for dl in dls:
            item = EsfItem()
            title = dl.xpath(".//h4[@class='clearfix']/a/@title")
            if title:
                item['title'] = title
            esfhousenews_url_text = dl.xpath(".//h4[@class='clearfix']/a/@href")[0]
            item['esfhousenews_url'] = esfhousenews_url_text
            info_lis = "".join(dl.xpath(".//p[@class='tel_shop']/text()")).split()
            for lis in info_lis:
                if '室' in lis:
                    # 户型
                    item['room_type'] = lis
                elif '㎡' in lis:
                    # 面积
                    item['area'] = lis
                elif '层' in lis:
                    if dl.xpath(".//p[@class='tel_shop']//a/text()"):
                        # 楼层
                        item['floor'] = dl.xpath(".//p[@class='tel_shop']//a/text()")[0].strip() + lis
                elif '向' in lis:
                    # 朝向
                    item['orientation'] = lis
                elif '年' in lis:
                    # 建筑时间
                    item['build_year'] = lis
            # 小区名字
            village_name = dl.xpath(".//p[@class='add_shop']/a/@title")
            if village_name:
                item['village_name'] = village_name[0]
            # 地址
            address = dl.xpath(".//p[@class='add_shop']/span/text()")
            if address:
                item['address'] = address[0]

            # 总价
            total_price = dl.xpath(".//dd[@class='price_right']/span[@class='red']/b/text()")
            if total_price:
                total_price = total_price[0] + '万元'
                item['total'] = total_price
            # 每平方米的价格

            unit_price = dl.xpath(".//dd[@class='price_right']/span[not(@class)]/text()")
            if unit_price:
                item['unit'] = unit_price[0]
            item_lis.append(item)
        return item_lis

    def parse_info_page(self, Html_document):
        item = EsfInfoItem()
        if type(Html_document) == str:
            xml_obj = etree.HTML(Html_document)
        else:
            xml_obj = etree.HTML('NoneType')

        title = xml_obj.xpath("//span[@class='tit_text']//text()")
        if title:
            item['title'] = title[0].strip()

        house_info_divs = xml_obj.xpath(
            "//div[contains(@class, 'tr-line clearfix')]//div[contains(@class,'trl-item1')]")

        if len(house_info_divs) == 6:
            # 户型
            room_type = house_info_divs[0].xpath(".//div[@class='tt']//text()")
            if room_type:
                item['room_type'] = room_type[0].strip()
            # 面积
            area = house_info_divs[1].xpath(".//div[@class='tt']//text()")
            if area:
                item['area'] = area[0].strip()
            # 单价
            unit_price = house_info_divs[2].xpath(".//div[@class='tt']//text()")
            if unit_price:
                item['unit_price'] = unit_price[0].strip()
            # 朝向
            orientation = house_info_divs[3].xpath(".//div[@class='tt']//text()")
            if orientation:
                item['orientation'] = orientation[0].strip()
            # 楼层
            floor_info = house_info_divs[4].xpath(".//div[@class='tt']//text()")
            floor_info_a = house_info_divs[4].xpath(".//div[@class='tt']//a//text()")
            floor_type = house_info_divs[4].xpath(".//div[@class='font14']//text()")
            if floor_info_a and floor_type:
                item['floor'] = floor_info_a[0].strip() + ',' + floor_type[0].strip()
            elif floor_info and floor_type:
                item['floor'] = floor_info[0].strip() + ',' + floor_type[0].strip()
            # 装修
            decoration = house_info_divs[5].xpath(".//div[@class='tt']//text()")
            decoration_a = house_info_divs[5].xpath(".//div[@class='tt']//a//text()")
            if decoration_a:
                item['decoration'] = decoration_a[0]
            elif decoration:
                item['decoration'] = decoration[0].strip()

            # 总价
        total_price = xml_obj.xpath("//div[contains(@class, 'price_esf')]/i//text()")
        if total_price:
            item['total_price'] = total_price[0].strip() + '万元'
        # 房源信息
        xpath_house_info_lis = xml_obj.xpath(
            "//div[contains(@class, 'content-item fydes-item')]//div[contains(@class, 'cont clearfix')]//div")
        for div in xpath_house_info_lis:
            if len(div.xpath(".//span//text()")) == 2:
                # 建筑年代
                if div.xpath(".//span//text()")[0].strip() == '建筑年代':
                    build_year = div.xpath(".//span//text()")[1]
                    item['build_year'] = build_year.strip()
        # 小区
        community = xml_obj.xpath("//a[@id='kesfsfbxq_A01_01_05']//text()")
        if community:
            item['community'] = community[0]
        # 小区信息
        xpath_community_info_lis = xml_obj.xpath("//div[contains(@class, 'cont pt30')]")
        if xpath_community_info_lis:
            xpath_community_info_lis = xpath_community_info_lis[0]
            # 小区信息顶栏
            for div in xpath_community_info_lis.xpath(".//div[contains(@class, 'topt clearfix')]//div"):
                # 小区参考均价
                if div.xpath(".//span//text()")[0].strip() == '参考均价':
                    community_price = div.xpath(".//span")[1].xpath(".//i//text()")
                    if community_price:
                        item['community_price'] = community_price[0].strip() + ' 元/平米'

                # 小区均价同比去年
                if div.xpath(".//span//text()")[0].strip() == '同比去年':
                    community_price_to_last_year = div.xpath(".//span")[1].xpath(".//em//span//text()")
                    if community_price_to_last_year:
                        item['community_price_to_last_year'] = community_price_to_last_year[0].strip()
                # 小区均价环比上月
                if div.xpath(".//span//text()")[0].strip() == '环比上月':
                    community_price_to_last_month = div.xpath(".//span")[1].xpath(".//em//span//text()")
                    if community_price_to_last_month:
                        item['community_price_to_last_month'] = community_price_to_last_month[0].strip()
            for div in xpath_community_info_lis.xpath(".//div[@class='clearfix']//div"):
                if len(div.xpath(".//span")) == 2:
                    # 绿化率
                    if '绿' in div.xpath(".//span//text()")[0].strip():
                        plant_rate = div.xpath(".//span//text()")[1]
                        if plant_rate:
                            item['plant_rate'] = plant_rate.strip()
                    # 小区容积率
                    if '容' in div.xpath(".//span//text()")[0].strip():
                        community_volume_rate = div.xpath(".//span//text()")[1]
                        if community_volume_rate:
                            item['community_volume_rate'] = community_volume_rate.strip()
                    # 小区总户数
                    if '户' in div.xpath(".//span//text()")[0].strip():
                        community_total_family_num = div.xpath(".//span//text()")[1]
                        if community_total_family_num:
                            item['community_total_family_num'] = community_total_family_num.strip()
                    # 产权年限
                    if div.xpath(".//span//text()")[0].strip() == '产权年限':
                        property_tenure = div.xpath(".//span//text()")[1]
                        if property_tenure:
                            item['property_tenure'] = property_tenure.strip() + '年'
                    # 小区总楼栋数
                    if div.xpath(".//span//text()")[0].strip() == '总楼栋数':
                        community_total_building_num = div.xpath(".//span//text()")[1]
                        if community_total_building_num:
                            item['community_total_building_num'] = community_total_building_num.strip()
                    # 小区物业费用
                    if div.xpath(".//span//text()")[0].strip() == '物业费用':
                        community_property_expenses = div.xpath(".//span//text()")[1]
                        if community_property_expenses:
                            item['community_property_expenses'] = community_property_expenses.strip()
                    # 小区人车分流
                    if div.xpath(".//span//text()")[0].strip() == '人车分流':
                        community_people_vehicles_depart = div.xpath(".//span//text()")[1]
                        if community_people_vehicles_depart:
                            item['community_people_vehicles_depart'] = community_people_vehicles_depart.strip()
        return item


class GetRandomUserAgent:
    with open('/home/oliver/PycharmProjects/scrapy_fang/user_agent.json', 'r', encoding='utf-8') as f:
        browser_dic = json.load(f)
        User_Agents = []
        for key in browser_dic.keys():
            User_Agents.extend(browser_dic[key])

    # 模拟浏览器请求头
    def agent_head(self,):
        user_agent = random.choice(self.User_Agents)
        head = {'User-Agent': user_agent}
        return head
