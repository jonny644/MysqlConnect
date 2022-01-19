#將Fred資料放進Mysql資料庫
from fredapi import Fred
import numpy as np
import matplotlib.pyplot as pp
import pandas as pd
import datetime as dt
import requests
import json
import configparser
import os
import time
import pymysql
import logging
import traceback

MYSQL_HOST = 'localhost'
MYSQL_DB = 'fredapi'
MYSQL_USER = 'root'
MYSQL_PASS = '000000'
config ={
    'host' : 'localhost', 
    'db' : 'fredapi', 
    'user' : 'root', 
    'password' : '000000',
    'charset' : 'utf8',
    'use_unicode' : True
}
datadir = "./fred/data/"
FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logging.basicConfig(level=logging.DEBUG, filename=datadir + 'fredapi.log', filemode='a', format=FORMAT)
# logger = logging.getLogger('fredapi_log')
# logger.setLevel(logging.DEBUG)

def connect_fred():  #連線 fred
    global fred, api_key
    api_key = '89931803c039b85e8d08254a3ae76f60'
    fred = Fred(api_key)

class MysqlConnect(object):
    def __init__(self, config):
        # Connect to the database
        self.connect = pymysql.connect(**config)
        db_Info = self.connect.get_server_info()
        # print("資料庫版本：", db_Info)
        self.cursor = self.connect.cursor()
        # self.cursor.execute('SELECT DATABASE()')
        # record = self.cursor.fetchone()
        sql = 'SELECT DATABASE()'
        record = self.Query(sql)
        # print("目前使用的資料庫：", record[0])
        logging.info('Open 資料庫版本：'+ db_Info + ' 資料庫：'+ record[0][0] )
 
    def Query(self, sql):
        try:
            self.cursor.execute(sql)
            return self.cursor.fetchall()
        except Exception as ex:
            logging.error("Exception:"+ str(ex))
            self.connect.ping()
            self.cursor = self.connect.cursor()
            self.cursor.execute(sql)
            return self.cursor.fetchall()

    def Insert(self, sql, item):
        try:
            self.cursor.execute(sql, item)
            self.connect.commit()
        except Exception as ex:
            logging.error("Exception:"+ str(ex))
            self.connect.ping()
            self.cursor = self.connect.cursor()
            self.cursor.execute(sql, item)
            self.connect.commit()

class ApiConnect(object):
    def __init__(self):
        pass

    def get_apidata(self, http_add):
        self.http_add = http_add
        # 先取得 API 完整資訊
        r = requests.get(self.http_add, verify = True)
        # fp = open(datadir + "r1.txt", "a")
        # fp.write(r.text)
        # fp.close()
        # print(r.text)
        full_release = r.json()
        lenth = len(full_release)
        dict_keys = list(full_release.keys())
        # print(lenth)
        full_release = r.json()[str(dict_keys[lenth-1])]
        return dict_keys[lenth-1], pd.DataFrame.from_dict(full_release)

    def get_columns_data(self,file_name, full_series):
        # full_series = get_apidata('https://api.stlouisfed.org/fred/release/series?release_id=51&realtime_start=1776-07-04&api_key='+api_key+'&file_type=json')# 先取得 api 的完整資訊
        # r = requests.get('https://api.stlouisfed.org/fred/release/series?release_id=51&realtime_start=1776-07-04&api_key='+api_key+'&file_type=json', verify = True)
        # full_series = r.json()['seriess']
        # 轉成 DataFrame，來看看這份完整資料長怎樣
        #full_series = pd.DataFrame.from_dict(full_series)
        self.file_name = file_name
        self.full_series = full_series
        # print(self.file_name)
        # print(self.full_series)
        datype = self.full_series.convert_dtypes().dtypes
        print(datype)
        z=-1
        df = pd.DataFrame(columns=['id','len'])
        for item in self.full_series.iterrows() :
            item = item[1].values.tolist()
            for i in range(16) :
                z=z+1
                df.loc[z] = [i,len(str(item[i]))]
                # print(i,type(item[i]),len(str(item[i])))

        df_max = pd.DataFrame(columns=['col_max','col_min'])
        for i in range(16) :
            df1 = df[df['id'] == i]
            df_max.loc[i] = [df1['len'].max(),df1['len'].min()]
            # print(i,df1['len'].max(),df1['len'].min())
        # df_max.to_csv(datadir + "df_max.csv")
        # print(df_max)
        # print(df.tail(5))
        # print(full_series.columns)

        for i in range(16) :
            df_type = str(datype[i])
            print(df_type)
            if df_type == 'Int64' :
              columns_type = 'int'
            elif df_type == 'float' :
                columns_type = 'float'
            elif df_type == 'bool' :
                columns_type = 'bool'
            else :
                if df_max.col_max[i] == 10 & df_max.col_min[i] == 10 :
                    columns_type = 'date'
                elif df_max.col_max[i] == 22 & df_max.col_min[i] == 22 :
                    columns_type = 'datetime'
                else :
                    columns_type = 'varchar('+ str(df_max.col_max[i]) +')'
            add_column = 'alter table '+self.file_name+' add column %s %s' % (str(full_series.columns[i]) , str(columns_type))
            print(add_column)
            freddb.Query(add_column)
            # logging.info('資料：'+ db_Info + ' 資料庫：'+ record[0][0] )
            return('sucess')

    def fill_columns_data(self,table_name, columns_data):
        self.table_name = table_name
        self.columns_data = columns_data
        #print(full_release.dtypes)
        # selectsql = 'describe ' +self.table_name  #查詢資料庫的欄位
        # print(selectsql)
        # table_columes = freddb.Query(selectsql)        
        keys = ', '.join(self.columns_data.columns)
        values = ', '.join(['%s'] * len(self.columns_data))
        insert = 'INSERT INTO {table}({keys}) VALUES ({values})'.format(table=self.table_name, keys=keys, values=values)

        for item in columns_data.iterrows() :
            item = item[1].values.tolist()
            # print(type(item[6]))
            item[5] =str(item[5]).replace('nan',' ')
            item[6] =str(item[6]).replace('nan',' ')
            # print(item)
            # selectsql = 'select * from ' +table_name ' where id = %s' % (item[0])  #查詢是否已經在資料庫的SQL
            # print(selectsql)
            # ret = freddb.Query(selectsql)
            if not ret:  #不在資料庫
                # print(item[1].values)
                print("id = ",item[0])
                # insert = 'INSERT INTO  ' +table_name +' (id, realtime_start, realtime_end, name, press_release, link, notes) VALUES(%s, %s, %s, %s, %s, %s, %s)'        
                freddb.Insert(insert, item)

def get_releases():
    table_name,full_release = apidb.get_apidata('https://api.stlouisfed.org/fred/releases?&realtime_start=1776-07-04&api_key='+api_key+'&file_type=json')
    # add_table = 'create table IF NOT EXISTS %s ()ENGINE=InnoDB DEFAULT CHARSET=utf8' % (table_name)
    #print(add_table)
    #freddb.Query(add_table)    
    series = apidb.get_columns_data(table_name,full_release)    # 先取得 FRED 大分類的完整資訊
    series = apidb.fill_columns_data(table_name,full_release)    
    # r = requests.get('https://api.stlouisfed.org/fred/releases?&realtime_start=1776-07-04&api_key='+api_key+'&file_type=json', verify = True)
    # full_release = r.json()['releases']
    # full_release = pd.DataFrame.from_dict(full_release)
    # print(full_release.dtypes)
    # full_release = full_release.convert_dtypes()

def change_colume(i,df_max, new_max):
    insert = 'alter table fred_releases change column %s %s varchar(%s)' % (df_max.col_name[i], df_max.col_name[i], str(new_max))
    try:
        print("change: ",i,df_max.col_name[i], new_max)
        cursor.execute(insert) 
        connect.commit()
        
    except:
        traceback.print_exc()
        connect.rollback()
        connect.close()
    
def get_series():
    table_name,full_series = apidb.get_apidata('https://api.stlouisfed.org/fred/release/series?release_id=9&realtime_start=1776-07-04&api_key='+api_key+'&file_type=json')
    add_table = 'create table IF NOT EXISTS %s (parend_id int)ENGINE=InnoDB DEFAULT CHARSET=utf8' % (table_name)
    print(add_table)
    freddb.Query(add_table)    
    series = apidb.get_columns_data(table_name,full_series)
    df_max = pd.read_csv(datadir + 'df_max.csv')
    cursor.execute('select id from fred_releases')
    # cursor.execute('select GROUP_CONCAT(REPLACE(path,‘/‘,‘,‘)) AS id from fred_releases')
    parend_id = cursor.fetchall()
    print(parend_id)
    # for release_id in range(len(parend_id)) :
    for release_id in parend_id :
        # 先取得 FRED 小分類的完整資訊
        # release_id = release_id.replace(',','')
        print(release_id[0])
        r = requests.get('https://api.stlouisfed.org/fred/release/series?release_id='+str(release_id[0])+'&realtime_start=1776-07-04&api_key='+api_key+'&file_type=json')
        
        full_series = r.json()['seriess']
        # 轉成 DataFrame，來看看這份完整資料長怎樣
        full_series = pd.DataFrame.from_dict(full_series)
        # print(full_series)
        for item in full_series.iterrows() :
            item = item[1].values.tolist()
            print(item)
            selectsql = "select * from fred_series where id = '%s'"% (item[0])  #查詢是否已經在資料庫的SQL
            print(selectsql)
            cursor.execute(selectsql)  #執行查詢的SQL
            ret = cursor.fetchone()  #如果有取出第一筆資料
            if not ret:  #不在資料庫# print(item[1].values)
                for i in (0,3,6,7,8,9,10,11,15) :
                    if df_max.col_max[i] < len(item[i]) :
                        df_max.col_max[i] = new_max
                        df_max.to_csv(datadir + "df_max.csv")
                        change_colume(i,df_max,len(item[i]))
                print("id = ",item[0])
                insert = 'INSERT INTO fred_series VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
                try:
                    cursor.execute(insert , (int(release_id[0]),str(item[0]), str(item[1]), str(item[2]), str(item[3]), str(item[4]), str(item[5]), str(item[6]), str(item[7]), str(item[8]), str(item[9]), str(item[10]), str(item[11]), str(item[12]), int(item[13]), int(item[14]), str(item[15])))
                    connect.commit()
                except:
                    connect.rollback()
                    connect.close()

connect_fred()
freddb = MysqlConnect(config)
apidb = ApiConnect()    
# connect_mysql()
# freddb.get_daily_data()
get_releases()
# get_series_columns()
# get_series()
freddb.cursor.close()
freddb.connect.close()
logging.info('Close 資料庫' )
print("資料庫連線已關閉")