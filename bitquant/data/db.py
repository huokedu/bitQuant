import auth
import api
import sql
import tools

import csv
import codecs
import numpy as np
from pandas import DataFrame
from sqlalchemy import create_engine,  MetaData
from sqlalchemy.sql import select

#|-------------------------------------------------
#|-----Connect to SQL data via dbconnect class-----

#|Connect to SQL database and create SQLAlchemy engine and MetaData
class dbconnect():	
	
	#|Connect to SQL database
	def __init__(self):	
		engine_str = auth.mysql()	
		self.eng = create_engine(engine_str)	
		self.conn = self.eng.connect()	
		self.meta = MetaData(self.eng)

	#|Load table variable and add to metadata
	def addtbl(self, table_name, create='no'):
		tbl = sql.tables(self.meta, table_name)
		if create == 'yes':
			self.meta.create_all(self.eng)
		return tbl

	#|Insert DataFrame to SQL table using "INSERT OR IGNORE" command
	def df_to_sql(self, df, table_name):
		tbl = self.addtbl(table_name)		
		df = df.to_dict('records')		
		ins = tbl.insert().prefix_with('IGNORE')
		ins.execute(df)	

	#|Return DataFrame from SQL table using filter arguments
	def sql_to_df(self, table_name, exchange='', start='',
			end='', source='', freq=''):
		tbl = self.addtbl(table_name)
		sel = select([tbl])	
	
		if exchange <> '':
			sel = sel.where(tbl.c.exchange == exchange)
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

		result = self.conn.execute(sel)
		headers = result.keys()
		result = result.fetchall()
		df = DataFrame(result, columns=headers)
		df = tools.date_index(df)
		return df

#|---------------------------------------------
#|-----Source specific SQL import commands-----

#|"Ping" exchange API for trade data and import into SQL database
def api_ping(exchange, limit=100):
	dbc = dbconnect()
	trd = api.trades(exchange, limit)	
	dbc.df_to_sql(trd, 'api')

#|Convert trade history to price and add to SQL database
def trades_to_pricedb(trd, freq, source):
	dbc = dbconnect()
	prc = tools.trades_to_price(trd, freq, source=source)
	prc['timestamp'] = prc.index.astype(np.int64) // 10**9
	prc['freq'] = freq
	dbc.df_to_sql(prc, 'price')

#|Import BitcoinCharts trade history CSV into SQL database
#|Before running, place CSV in 'modules' folder and rename file to exchange name
def import_bchart(exchange, start):
	dbc = dbconnect()
	trd = api.bchart(exchange, start)
	trd['exchange'] = exchange
	dbc.df_to_sql(trd, 'bchtrades')
