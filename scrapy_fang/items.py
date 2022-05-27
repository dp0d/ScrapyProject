# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class UrlItem(scrapy.Item):
    # 省份
    province = scrapy.Field()
    # 城市
    city = scrapy.Field()
    # 二手房链接
    esfhouse_url = scrapy.Field()


#二手房页面的Item
class EsfItem(scrapy.Item):
      # 省份
      province = scrapy.Field()
      # 城市
      city = scrapy.Field()
      #二手房的标题
      title = scrapy.Field()
      # 二手房详细信息的链接
      esfhousenews_url = scrapy.Field()
      # 户型
      room_type = scrapy.Field()
      # 面积
      area = scrapy.Field()
      # 楼层
      floor = scrapy.Field()
      # 朝向
      orientation = scrapy.Field()
      # 建筑时间
      build_year = scrapy.Field()
      # 小区名字
      village_name = scrapy.Field()
      # 地址
      address = scrapy.Field()
      # 总价
      total = scrapy.Field()
      #每平米的价格
      unit = scrapy.Field()


class EsfInfoItem(scrapy.Item):
    # 详情页链接
    esf_link = scrapy.Field()
    # 省份
    province = scrapy.Field()
    # 城市
    city = scrapy.Field()
    # 二手房的标题
    title = scrapy.Field()
    # 户型
    room_type = scrapy.Field()
    # 面积
    area = scrapy.Field()
    # 单价
    unit_price = scrapy.Field()
    # 朝向
    orientation = scrapy.Field()
    # 楼层
    floor = scrapy.Field()
    # 装修
    decoration = scrapy.Field()
    # 总价
    total_price = scrapy.Field()
    # 小区
    community = scrapy.Field()
    # 建筑年代
    build_year = scrapy.Field()
    # 绿化率
    plant_rate = scrapy.Field()
    # 产权年限
    property_tenure = scrapy.Field()
    # 小区参考均价
    community_price = scrapy.Field()
    # 小区均价同比去年
    community_price_to_last_year = scrapy.Field()
    # 小区均价同比上月
    community_price_to_last_month = scrapy.Field()
    # 小区容积率
    community_volume_rate = scrapy.Field()
    # 小区总楼栋数
    community_total_building_num = scrapy.Field()
    # 小区总户数
    community_total_family_num = scrapy.Field()
    # 小区物业费用
    community_property_expenses = scrapy.Field()
    # 小区物业费用
    community_people_vehicles_depart = scrapy.Field()

