from Backtester import Backtester
from TradingBot import TradingBot

if __name__ == "__main__":    
    bt = Backtester(["IWD", "IWF"], swap_positions=True)
    trade_date = bt.path_dependency_test("01-Jan-2000", "01-Jan-2021")