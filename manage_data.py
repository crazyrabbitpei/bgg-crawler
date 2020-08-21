import sqlite3
import pandas as pd
from sqlalchemy import Table, Column
from sqlalchemy.types import Integer, String, DateTime, Text
import sqlalchemy
import logging
from logging.handlers import TimedRotatingFileHandler

import sys

from tool.MyLogger import MyLogger

logger = MyLogger(log_path='./logs',
                  log_file='{0}.log'.format(__name__), name=__name__)

class DataManage:

    def __init__(self, dbname):
        self.connect_db(dbname)

    def connect_db(self, dbname):
        self.connection = sqlite3.connect(dbname)
        self.cursor = self.connection.cursor()

        self.dbname = dbname

    def create_table(self, tname=None, csv_file=None):
        if not tname:
            raise ValueError('table name not defined')
        if not csv_file:
            raise ValueError('initial csv file not defined')

        df = pd.read_csv(csv_file)
        logger.debug(pd.io.sql.get_schema(df, tname))

        df.to_sql(tname, self.connection, if_exists='replace',
                  index=False)

    def select_table(self, tname):
        return pd.read_sql_query("SELECT * FROM {0}".format(tname), self.connection)

    def get_bg_ids_from_rank(self, id_field_name=None, tname=None, limit=10):
        df = pd.read_sql_query("SELECT {0} FROM {1} limit {2}".format(
            id_field_name, tname, limit), self.connection)
        return df[id_field_name].values.tolist()

    def close_connection(self):
        self.connection.close()


# dbname = sys.argv[1]
# tname = sys.argv[2]
# # csv_file = sys.argv[3]

# manage = DataManage('{0}.db'.format(dbname))
# #manage.create_table(tname, csv_file=csv_file)
# #df = manage.select_table(tname)
# ids = manage.get_bg_ids_from_rank('id', tname)
# print(ids)
# for id in ids:
#     print(id)
# manage.close_connection()
