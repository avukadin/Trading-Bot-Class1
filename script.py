from Backtester import Backtester
from TradingBot import TradingBot

#tb = TradingBot(["IWD", "IWF"])
#tb.check_for_trades("IWD")


if __name__ == "__main__":    
    
    bt = Backtester(["IWD", "IWF"])
    trade_date = bt.path_dependency_test("01-Jan-2000", "01-Jan-2015")