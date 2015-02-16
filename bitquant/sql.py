import auth
import tools

import csv
import codecs
import numpy as np
from pandas import DataFrame
from sqlalchemy import create_engine,  MetaData
from sqlalchemy.sql import select
from sqlalchemy import Table, Column, Integer, String, Float, DateTime

#|------------------------------------------------------
#|--------Connect to SQL data via dbconnect class-------

#|Connect to SQL database and create SQLAlchemy engine and MetaData
class dbconnect():	
	
	#|Connect to SQL database
	def __init__(self):	
		engine_str = auth.mysql()	
		self.eng = create_engine(engine_str)	
		self.conn = self.eng.connect()	
		self.meta = MetaData(self.eng)

	#|Load table variable and add to metadata
	def add_tbl(self, table_name, create='no'):
		tbl = self.tables(table_name)
		if create == 'yes':
			self.meta.create_all(self.eng)
		return tbl

	#|Insert DataFrame to SQL table using "INSERT OR IGNORE" command
	def df_to_sql(self, df, table_name):
		tbl = self.add_tbl(table_name)		
		df = df.to_dict('records')		
		ins = tbl.insert().prefix_with('IGNORE')
		ins.execute(df)	

	#|Return DataFrame from SQL table using filter arguments
	def sql_to_df(self, table_name, exchange='',  symbol='',
				start='', end='', source='', freq=''):
		tbl = self.add_tbl(table_name)
		sel = select([tbl])	
	
		#|Build select statement using input parameters
		if exchange <> '':
			sel = sel.where(tbl.c.exchange == exchange)
		if symbol <> '':
			sel = sel.where(tbl.c.symbol == symbol)
		if start <> '':
			if isinstance(start, str):			
				start = tools.dateconv(start)
			sel = sel.where(tbl.c.timestamp >= start)
		if end <> '':
			if isinstance(end, str):
				end = tools.dateconv(end)
			sel = sel.where(tbl.c.timestamp <= end)
		if source <> '':
			sel = sel.where(tbl.c.source == source)
		if freq <> '':
			sel = sel.where(tbl.c.freq == freq)

		#|Request data from MySQL server and format
		result = self.conn.execute(sel)
		headers = result.keys()
		result = result.fetchall()
		df = DataFrame(result, columns=headers)
		#|Create datetime index if data has 'timestamp' column		
		try:		
			df = tools.date_index(df)
		except:
			pass
		return df
	
	#|Load SQLAlchemy table into MetaData with option to 'create'
	#|SQL table in database
	def tables(self, table_name):	

		if table_name == 'trades':
			tbl = Table(table_name, self.meta, Column('tid', Integer, primary_key=True),
				Column('price', Float), Column('amount', Float),
				Column('type', String(4)), Column('timestamp', Integer),
				Column('timestamp_ms', Integer), 
				Column('exchange', String(20), primary_key=True),
				Column('symbol', String(6), primary_key=True))
		if table_name == 'price':
			tbl = Table(table_name, self.meta, 
				Column('timestamp', Integer, primary_key=True),
				Column('price', Float), Column('amount', Float),
				Column('open', Float), Column('high', Float),
				Column('low', Float),
				Column('freq', String(5), primary_key=True), 
				Column('exchange', String(20), primary_key=True),
				Column('symbol', String(6), primary_key=True),
				Column('source', String(3), primary_key=True))
		if table_name == 'exchanges':
			tbl = Table(table_name, self.meta,
				Column('exchange', String(20), primary_key=True),
				Column('symbol', String(6), primary_key=True),
				Column('url', String(50)), Column('trade', String(50)),
				Column('limit', String(20)), Column('since', String(20)),
				Column('market', String(20)),Column('quandl', String(50)), 
				Column('bchart', String(20)),Column('last_touch', Integer))
		if table_name == 'last':
			tbl = Table(table_name, self.meta,
				Column('exchange', String(20), primary_key=True),
				Column('symbol', String(6), primary_key=True),
				Column('freq', String(5), primary_key=True),
				Column('last', Integer))
		return tbl


class trades_to_price(object):
	
	def __init__(self):
		self.keys = DataFrame(columns=('exchange','symbol','freq'))
		self.db = dbconnect()

	def add_key(self, exchange, symbol, freq):
		self.keys = self.keys.append([exchange, symbol, freq])

	def run_keys(self):		
		last = sql.last_df()
		last = last.join(self.keys).dropna()
		start = last['last'].min()
		df = self.db.sql_to_df('trades',start=start)
		#for exchange in self.keys['exchange'].unique():
		#	trades_to_price(trd, exchange

	def convert(trd, freq, exchange=''):
		if exchange <> '':
			trd = trd[trd['exchange'] == exchange] 
		prc = tools.trades_to_price(trd, freq)
		prc['timestamp'] = prc.index.astype(np.int64) // 10**9
		prc['freq'] = freq
		prc['source'] = 'trades'
		self.db.df_to_sql(prc, 'price')		
		
#|------------------------------------------------------
#|--------Shortcut SQL to DataFrame commands--------

#|Add Dataframe into SQL database
def df_to_sql(df, table_name):
	db = dbconnect()
	db.df_to_sql(df, table_name)

#|Pull trades data from SQL table and convert to DataFrame
def trades_df(exchange='', start ='', end=''):		
	db = dbconnect()	
	df = db.sql_to_df('trades', exchange=exchange,
			start=start, end=end)
	return df

#|Return price history DataFrame using exchange/source filters
def price_df(exchange='', freq='', source=''):
	db = dbconnect()
	df = db.sql_to_df('price', exchange=exchange,
			source=source, freq=freq)
	return df

#|Return last timestamp table
def last_df():
	db = dbconnect()
	df = db.sql_to_df('exchanges')
	return df

#|Return exchange information table
def exchanges_df(exchange='', symbol=''):
	db = dbconnect()
	df = db.sql_to_df('exchanges',
		exchange=exchange, symbol=symbol)
	return df
