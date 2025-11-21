from utils import get_dynamodb
import os
import pandas as pd
import yfinance as yf


class Trader:
    def __init__(self):
        assert os.getenv('DYNAMO_TABLE_NAME', None), "DYNAMO_TABLE_NAME not set"
        self.dynamodb = get_dynamodb()
        self.dynamodb_table_name = os.getenv('DYNAMO_TABLE_NAME', None)
        self.df = self._read_data_from_aws()
        self._clean_data()
        self._filter_data()
        self.open_trades = {} # not going to implement for this example, need to connect to brokerage api etc.
        self.options_tables = {}
        self.current_prices = {}


    def _read_data_from_aws(self) -> pd.DataFrame:
        table = self.dynamodb.Table(self.dynamodb_table_name)
        response = table.scan()
        data = response.get('Items', [])
        while response.get('LastEvaluatedKey') is not None:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response.get('Items', []))
        return pd.DataFrame(data)


    def _clean_data(self):
        self.df = self.df[self.df['Ticker'].notna()]
        self.df['Date'] = pd.to_datetime(self.df['Date'])
        self.df.loc[:, 'year'] = self.df['Date'].dt.year
        self.df.loc[:, 'month'] = self.df['Date'].dt.month
        self.df.loc[:, 'day'] = self.df['Date'].dt.day
        # if purchase, then position is long, else short
        self.df.loc[:, 'position'] = self.df['Tx_Type'].apply(lambda x: 'long' if x.lower() == 'purchase' else 'short')
        self.df['trade'] = None


    def _filter_data(self):
        today = pd.Timestamp.now()
        last_30_days = today - pd.Timedelta(days=30)
        self.df = self.df[self.df['Date'] >= last_30_days]


    def _get_options(self, symbol: str, expiry: pd.Timestamp) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        avail = ticker.options
        if not avail:
            return pd.DataFrame()
        avail_dates = [pd.to_datetime(d) for d in avail]
        # choose the available expiry closest to the requested expiry
        closest = min(avail_dates, key=lambda d: abs(d - expiry))
        options = ticker.option_chain(closest.strftime('%Y-%m-%d'))
        calls = options.calls.copy()
        puts = options.puts.copy()
        calls['type'] = 'call'
        puts['type'] = 'put'
        all_options = pd.concat([calls, puts], ignore_index=True)
        return all_options


    def _get_atm_call(self, options_df: pd.DataFrame, current_price: float):
        calls = options_df[options_df['type'] == 'call']
        atm_calls = calls.iloc[(calls['strike'] - current_price).abs().argsort()[:1]]
        if not atm_calls.empty:
            row = atm_calls.iloc[0]
            return row.to_dict()
        return None


    def _get_atm_put(self, options_df: pd.DataFrame, current_price: float):
        puts = options_df[options_df['type'] == 'put']
        atm_puts = puts.iloc[(puts['strike'] - current_price).abs().argsort()[:1]]
        if not atm_puts.empty:
            row = atm_puts.iloc[0]
            return row.to_dict()
        return None


    def _get_current_price(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='1d')
        if hist.empty:
            return None
        return hist['Close'][0]


    def get_trades(self):
        for row in self.df.itertuples(index=True):
            i = row.Index
            symbol = row.Ticker

            # Current Price Retrieval
            if symbol not in self.current_prices:
                self.current_prices[symbol] = self._get_current_price(symbol)
            current_price = self.current_prices[symbol]
            if not current_price:
                continue

            # Options Table Retrieval
            target_expiry = pd.Timestamp(row.Date) + pd.Timedelta(days=90)
            options_key = f"{symbol}_{target_expiry.strftime('%Y-%m-%d')}"

            options_df = self.options_tables.get(options_key)
            if options_df is None:
                options_df = self._get_options(symbol, target_expiry)
                self.options_tables[options_key] = options_df
            if options_df.empty:
                continue

            # Trade Logic
            call_option = self._get_atm_call(options_df, current_price)
            put_option = self._get_atm_put(options_df, current_price)
            trade = {
                'buy': call_option if row.position == 'long' else put_option,
                'sell': put_option if row.position == 'long' else call_option
            }
            self.df.at[i, 'trade'] = trade


    def save_csv(self):
        with open('trades.csv', 'w') as f:
            self.df.to_csv(f, index=False)


    def execute_trades(self):
        # Placeholder for trade execution logic
        pass
