# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
# useful for handling different item types with a single interface
from scrapy.exporters import CsvItemExporter
from scrapy_fang.items import EsfItem, UrlItem, EsfInfoItem


class ScrapyFangPipeline(object):

    def open_spider(self, spider):
        # # URL
        # self.url_fp = open('esf_url.csv', 'wb')
        # self.url_exporter = CsvItemExporter(self.url_fp)

        # # 二手房信息
        # self.esf_info_fp = open('esf_info.csv', 'wb')
        # self.esf_info_exporter = CsvItemExporter(self.esf_info_fp)

        # 二手房详情信息
        self.esf_detail_info_fp = open('esf_detail_info.csv', 'wb')
        self.esf_detail_info_exporter = CsvItemExporter(self.esf_detail_info_fp)

    def process_item(self, item, spider):
        # # 处理URL
        # if isinstance(item, UrlItem):
        #     print("存放二手房链接信息")
        #     self.url_exporter.export_item(item)

        # # 处理二手房信息
        # if isinstance(item, EsfItem):
        #     print("存放二手房房源信息")
        #     self.esf_info_exporter.export_item(item)

        # 处理详情页信息
        if isinstance(item, EsfInfoItem):
            print("存放二手房房源详情信息")
            self.esf_detail_info_exporter.export_item(item)

        # 返回是必须的，告诉引擎item已经处理完成了，可以继续执行后面代码。
        return item

    def close_spider(self, spider):
        # self.esf_info_fp.close()
        # self.url_fp.close()
        self.esf_detail_info_fp.close()
