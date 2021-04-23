import yfinance as yf 
import pickle
import numpy as np
import datetime

debugTF = True

class TradingBot():
    
    raw_data = None
    trade_data = None
    
    debug_data = "C:/Users/Alex/Projects/SkillShare/data"
    tickers = None
    signal_length = None
    swap_positions = False
    
    NO_CHANGE = 0
    NEW_POSITION = 1
    EXIT_POSITION = 2
    CHANGE_POSITION = 3
    
    def __init__(self, tickers=None, signal_length=200, swap_positions=False):
        self.tickers = tickers
        self.signal_length = signal_length
        self.swap_positions = swap_positions
        
        # Load all the data
        if debugTF:
            self.load_pickle()
        else:
            self.raw_data = self._query_data(self.tickers)
            self.save_pickle()
            
        self.trade_data = self._prepare_trade_data()
        
    def check_for_trades(self, current_position):
        day_data = self.trade_data.iloc[-1]
        last_date = str(self.trade_data.index[-1])
        next_position, status = self._make_trade_decision(day_data, current_position)        
        print(f'Most Recent Data Availbale: {last_date}')
        print(f'Current Position: {current_position}')
        print(f'Next Position: {next_position}')        
  
    def _query_data(self, tickers):
        start_date, end_date = self._get_query_range()
        tickers = ' '.join(tickers)
        hist = yf.download(tickers, start=start_date, end=end_date)
        hist = hist.sort_values('Date', ascending=True)
        return hist
    
    def _get_query_range(self):
        today = datetime.date.today()
        start_date = today - datetime.timedelta(self.signal_length*2)
        end_date = str(today)
        return start_date, end_date
    
    def _calc_signals(self, data):
        for ticker in self.tickers:
            data.loc[:,("Signal", ticker)] = data["Close", ticker].rolling(window=self.signal_length).apply(self._get_slope, raw=False).shift(1)
            data.loc[:,("Signal", ticker)] = data["Signal", ticker]/data["Close", ticker]
        return data
    
    def _add_prev_close(self, data):
        for ticker in self.tickers:            
            data.loc[:,("Prev_Close", ticker)] = data["Close", ticker].shift(1)
        return data
            
    def _prepare_trade_data(self):
        # Gather data for backtes
        trade_data = self.raw_data[["Close", "Open"]]
        trade_data = self._calc_signals(trade_data)
        trade_data = self._add_prev_close(trade_data)
        trade_data = self._remove_nans(trade_data)
        
        return trade_data
    
    def _make_trade_decision(self, day_data, prev_position):
        
        next_position = prev_position
        status = self.NO_CHANGE
        
        # Find the strongest signal
        ndx = np.argmax(day_data["Signal"])
        strongest_ticker = day_data["Signal"].index[ndx]
        strongest_signal = day_data["Signal", strongest_ticker]
        
        # Not currently in a trade, look for an entry
        if prev_position is None:           
            if strongest_signal>0:
                next_position = strongest_ticker
                status = self.NEW_POSITION
            
        # Currently in a position
        else:
            signal = day_data["Signal", prev_position]
            
            # Change to a better momentum stock
            if (self.swap_positions) and (strongest_signal>signal*1.1) and (strongest_signal>0):
                next_position = strongest_ticker
                status = self.CHANGE_POSITION

            # Exit Position
            elif signal<=0:
                next_position = None
                status = self.EXIT_POSITION
        
        return next_position, status
    
    @staticmethod
    def _filter_dates(data, start_date, end_date):
        data = data.loc[start_date:end_date]
        return data
    
    @staticmethod
    def _remove_nans(data):
        nan_filter = ~np.any(data["Signal"].isnull(), 1)
        return data[nan_filter]
    
    @staticmethod
    def _get_slope(array):
        y = np.array(array)
        x = np.arange(len(y))
        slope, _ = np.polyfit(x,y, deg=1)
        return slope

    # ============== DEBUG ======================= 
    def save_pickle(self):
        with open(self.debug_data, 'wb' ) as outfile:
            pickle.dump(self.raw_data, outfile)

    def load_pickle(self):
        with open(self.debug_data, 'rb' ) as file:    
            data = pickle.load(file)
            self.raw_data = data