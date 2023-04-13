from github import Github
from model import GithubDB
from tqdm import tqdm
import logging
import time
import io

class TqdmToLogger(io.StringIO):

    logger = None
    level = None
    buf = ''

    def __init__(self, logger, level=None):
        super(TqdmToLogger, self).__init__()
        self.logger = logger
        self.level = level or logging.INFO

    def write(self, buf):
        self.buf = buf.strip('\r\n\t ')

    def flush(self):
        self.logger.log(self.level, self.buf)

class GithubMonitor:
    def __init__(self, username, password, db):
        self.github = Github(username, password)
        self.db = db
        self.keywords_for_search = []
        self.logger = logging.getLogger(__name__+".GithubMonitor")
        self.tqdmout = TqdmToLogger(self.logger, level=logging.INFO)

    def update(self):
        for kw in self.keywords_for_search:
            self.logger.info("Search Keyword: " + kw)
            pages = self.github.search_code(kw.encode('utf-8'), sort="indexed", order="desc")
            try:
                total = pages.totalCount
            except Exception as e:
                print("get total count failed")
                time.sleep(60)
                total = pages.totalCount

            tqdmout = TqdmToLogger(self.logger, logging.INFO)
            it = iter(tqdm(range(min(1000, total)), file=tqdmout, mininterval=30))

            for i in range(0, 34):
                try:
                    items = pages.get_page(i)
                except Exception as e:
                    logging.error(e.message)
                    time.sleep(60)
                    try:
                        items = pages.get_page(i)
                    except Exception as e:
                        continue

                for item in items:
                    try:
                        self.db.add_data_from_obj(item, kw.split(" "))
                        it.next()
                    except Exception as e:
                        logging.error(e.message)
                        pass

    def add_keywords_for_search(self, keywords):
        self.keywords_for_search.extend(keywords)

    def close(self):
        self.db.close()
