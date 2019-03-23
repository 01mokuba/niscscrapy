-- MySQLとの接続に使用しているMySQL-pythonがPython3に対応していないのか、3/17に試してみて上手くいかないので、対応を考えています。 --
3/23 別の部分のミスでした。

# niscscrapy

* Scrapyを使用
* WebページのURLとタイトルを出力
* 出力先はCSVファイルとMySQL
* 今回は例としてNISCのWebサイト https://www.nisc.go.jp を対象とする



## MySQL側の操作・準備

一般的なMySQL操作と同様。以下の通り設定する。

```mysql:データベース作成
# MySQLサーバに接続
$ mysql -u root -p

# データベース名：niscscraping
# デフォルト文字コード：4バイト対応のUTF-8
mysql> CREATE DATABASE niscscraping DEFAULT CHARACTER SET utf8mb4;

# localhostから接続可能なユーザscraperを作成
# scraperのパスワード：password
mysql> CREATE USER scraper@localhost IDENTIFIED BY 'password';

# scraperにniscscrapingの読み書き権限を付与
mysql> GRANT ALL ON niscscraping.* TO scraper@localhost;
```

また、PythonからMySQLに接続するために、ライブラリmysqlclientをインストールする。

`$ pip install mysqlclient `



## Scrapyの編集

### プロジェクトの開始

niscscrapyというプロジェクトを作成する。

` $ scrapy startproject niscscrapy` 

niscscrapyのディレクトリに移動し、各ファイルを編集する。

```
$ tree niscscrapy/
niscscrapy/
├── niscscrapy
│   ├── __init__.py
│   ├── __pycache__
│   ├── items.py
│   ├── middlewares.py
│   ├── pipelines.py
│   ├── settings.py
│   └── spiders
│       ├── __init__.py
│       └── __pycache__
└── scrapy.cfg
```

基本的にはサンプルのファイルを参照（コピーすればそのまま使えるはず）。



#### settings.pyの編集

以下の部分のコメントアウトを外す。（バージョンにより異なる可能性あり）

* DOWNLOAD_DELAY = 3 # 対象サーバに負荷をかけないため。1秒以上あればOK。
* ITEM_PIPELINES = … 以下の3行



#### items.pyの編集

```python:items.py
import scrapy


class NiscscrapyItem(scrapy.Item):
    # URLとtitleのフィールドを作成
    URL = scrapy.Field()
    title = scrapy.Field()
```



#### pipeline.pyの編集

```python:pipline.py
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
```



#### Spiderの作成

scrapy genspiderコマンドを利用してSpiderを自動生成する。（Spider名と対象URLを設定）

` scrapy genspider niscspider www.nisc.go.jp `

spiderのディレクトリに生成された、niscspider.pyを以下の通り編集する。

```python:niscspider.py
import scrapy

from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.selector import Selector
from niscscrapy.items import NiscscrapyItem

class NiscspiderSpider(CrawlSpider):
    # spiderの名称、クローリングの対象を設定
    name = 'niscspider'
    allowed_domains = ['www.nisc.go.jp']
    start_urls = ['https://www.nisc.go.jp/']

    # ルールの設定
    rules = (
    # 指定URL以下、全てのページを対象にparse_pageinfoを実行
    Rule(LinkExtractor(allow=r'/'), callback='parse_pageinfo', follow=True),
    )

    # parse_pageinfoの定義
    def parse_pageinfo(self, response):
        sel = Selector(response)
        item = NiscscrapyItem()
        item['URL'] = response.url
        # ページのどの部分をスクレイプするかを指定
        # ここではxPath形式でタイトルタグのテキストを指定
        item['title'] = sel.xpath('/html/head/title/text()').extract()
        return item
```



## 実行

` scrapy crawl niscspider -o result.csv`

MySQLに結果が挿入されるほか、spiderのディレクトリにCSV形式でも出力される。
