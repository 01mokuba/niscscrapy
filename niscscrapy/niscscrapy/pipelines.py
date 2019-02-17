# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import MySQLdb

class NiscscrapyPipeline(object):
    """
    ItemをMySQLに保存するPipeline
    """

    def open_spider(self, spider):
        """
        Spiderの開始時にMySQLサーバに接続する
        itemsテーブルが存在しない場合は作成する
        """

        settings = spider.settings # settings.pyから設定を読み込む
        params = {
            'host': settings.get('MYSQL_HOST', 'localhost'), # ホスト
            'db': settings.get('MYSQL_DATABASE', 'niscscraping'), # データベース名
            'user': settings.get('MYSQL_USER', 'scraper'), # ユーザ名
            'passwd': settings.get('MYSQL_PASSWORD', 'password'), # パスワード
            'charset': settings.get('MYSQL_CHARSET', 'utf8mb4'), # 文字コード
        }
        self.conn = MySQLdb.connect(**params) # MySQLサーバに接続
        self.c = self.conn.cursor() # カーソルを取得
        # itemsテーブルが存在しない場合は作成
        # URLカラムとtitleカラムを作成
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER NOT NULL AUTO_INCREMENT,
                URL CHAR(200) NOT NULL,
                title CHAR(200) NOT NULL,
                PRIMARY KEY (id)
            )
        ''')
        self.conn.commit() # 変更をコミット

    def close_spider(self, spider):
        """
        Spiderの終了時にMySQLサーバへの接続を切断する
        """

        self.conn.close()

    def process_item(self, item, spider):
        """
        Itemをitemsテーブルに挿入する
        """

        # URLとtitleを挿入
        # self.c.execute('INSERT INTO items (title) VALUES (%(title)s)', dict(item))
        self.c.execute('INSERT INTO items (URL, title) VALUES (%(URL)s, %(title)s)', dict(item))
        self.conn.commit() # 変更をコミット
        return item

