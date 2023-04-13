from sqlalchemy import Column, DateTime, String, Integer, Text, ARRAY, Boolean,func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_
from github.ContentFile import ContentFile
from datetime import timedelta, datetime
from dateutil import parser
import json
import re

Base = declarative_base()

def uni_time(date):
    return date.strftime("%Y-%m-%d")

def parse_html_url(html_url):

    sre = re.match("https://github\.com/[^/]+/[^/]+/blob/[^/]+/(.*)", html_url)

    return sre.groups()[0] if sre else ""

class SetType(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        return json.dumps(list(value))

    def process_result_value(self, value, dialect):
        return set(json.loads(value))

    def copy(self):
        return SetType(self.impl.length)


class Github(Base):
    __tablename__ = "github"

    sha = Column(Text(40), nullable=False, primary_key=True)
    name = Column(Text, nullable=False)
    html_url = Column(Text, nullable=False)
    last_modified = Column(DateTime)
    repository = Column(Text, nullable=False)
    keywords = Column(SetType, nullable=False)
    update_date = Column(DateTime, nullable=False)
    isnew = Column(Boolean, nullable=False)
    git_url = Column(Text, nullable=True)

    def to_dict(self):
        return dict((c.name, getattr(self, c.name, None)) for c in self.__table__.columns)

class GithubDB:

    def __init__(self, dbname):
        engine = create_engine('sqlite:///'+dbname)
        session = sessionmaker()
        session.configure(bind=engine)
        Base.metadata.create_all(engine)

        self.session = session()

    def close(self):
        self.session.close()

    def add_data_from_obj(self, obj, keywords):
        keys = Github.__table__.columns
        obj_dict = dict((k.name, getattr(obj, k.name, None)) for k in keys)
        obj_dict['keywords'] = set(keywords)
        obj_dict['update_date'] = datetime.now()
        obj_dict['repository'] = obj_dict['repository'].full_name
        obj_dict['last_modified'] = datetime.now()

        items = self.session.query(Github).filter(Github.sha==obj_dict['sha'])
        #in the same turn, code may be indexed by different keywords so that items.count() > 1
        if items.count() == 1:
            #threse are the old code or the code added by different keywords
            item = items.first()
            kwds = item.keywords
            kwds.update(set(keywords))
            items.update({Github.keywords: kwds,
                          Github.update_date: datetime.now(),
                          Github.git_url: obj_dict['git_url']}, synchronize_session=False)
            self.session.commit()
        else:
            #these are entirely the new code 
            same_file_name_in_repo = self.session.query(Github).filter(and_(Github.name==obj_dict['name'],
                                                      Github.repository==obj_dict['repository']))
            filepath = parse_html_url(obj_dict['html_url'])
            if len(filter(lambda x: parse_html_url(x.html_url) == filepath, same_file_name_in_repo)) == 0:
                obj_dict['isnew'] = True
            else:
                obj_dict['isnew'] = False

            self.session.add(Github(**obj_dict))
            self.session.commit()

    def get_new_datas(self):
        return filter(lambda item: datetime.now() - item['last_modified'] < timedelta(hours=10)
                 , self.get_recent_datas())


    def get_datas_by_date(self, date):
        todate = date
        fromdate = todate - timedelta(hours=10)

        datas = self.session.query(Github).filter(
            Github.update_date >= fromdate,
            Github.update_date < todate
        )

        return [d.to_dict() for d in datas]

    def get_recent_datas(self):
        now = datetime.now()
        return self.get_datas_by_date(now)
