"""
MT5 Trade Executor
Execute real trades on MetaTrader 5

Features:
- Place market orders
- Place limit orders
- Modify orders
- Close positions
- Get order/position status
"""

import MetaTrader5 as mt5
import logging
from typing import Optional, Tuple, Dict
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """MT5 Order types"""
    BUY = mt5.ORDER_TYPE_BUY
    SELL = mt5.ORDER_TYPE_SELL
    BUY_LIMIT = mt5.ORDER_TYPE_BUY_LIMIT
    SELL_LIMIT = mt5.ORDER_TYPE_SELL_LIMIT
    BUY_STOP = mt5.ORDER_TYPE_BUY_STOP
    SELL_STOP = mt5.ORDER_TYPE_SELL_STOP


@dataclass
class TradeResult:
    """Result from trade execution"""
    success: bool
    order_ticket: Optional[int]
    volume: float
    price: float
    comment: str
    error_code: Optional[int] = None
    error_description: Optional[str] = None
    
    def __str__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"Trade {status}: Ticket={self.order_ticket}, Vol={self.volume}, Price={self.price}"


class MT5TradeExecutor:
    """
    Execute trades on MT5
    
    Example:
        >>> executor = MT5TradeExecutor()
        >>> result = executor.place_market_order(
        >>>     symbol='XAUUSD',
        >>>     order_type='BUY',
        >>>     volume=0.01,
        >>>     sl=2600,
        >>>     tp=2700
        >>> )
    """
    
    def __init__(self, 
                 magic_number: int = 234000, 
                 volume_multiplier: float = 1.0,
                 primary_symbol: str = 'XAUUSD',
                 secondary_symbol: str = 'XAGUSD'):
        """
        Initialize trade executor
        
        Args:
            magic_number: Magic number for identifying bot trades
            volume_multiplier: Multiplier for all order volumes (default 1.0)
                              Examples:
                              - 1.0  = Normal size (0.02 lots)
                              - 10.0 = 10x size (0.20 lots) - Better hedge ratio accuracy!
                              - 0.1  = 0.1x size (0.002 lots) - For testing
            primary_symbol: Primary symbol (default: XAUUSD)
            secondary_symbol: Secondary symbol (default: XAGUSD)
        """
        self.magic_number = magic_number
        self.volume_multiplier = volume_multiplier
        self.primary_symbol = primary_symbol
        self.secondary_symbol = secondary_symbol
        
        if not mt5.initialize():
            raise RuntimeError("MT5 initialization failed")
        
        logger.info(f"MT5TradeExecutor initialized (magic={magic_number}, "
                   f"volume_multiplier={volume_multiplier}x, "
                   f"symbols={primary_symbol}/{secondary_symbol})")
    
    def place_market_order(self,
                          symbol: str,
                          order_type: str,
                          volume: float,
                          sl: Optional[float] = None,
                          tp: Optional[float] = None,
                          deviation: int = 20,
                          comment: str = "PairBot") -> TradeResult:
        """
        Place market order
        
        Args:
            symbol: Trading symbol (XAUUSD, XAGUSD)
            order_type: 'BUY' or 'SELL'
            volume: Order volume (lots)
            sl: Stop loss price
            tp: Take profit price
            deviation: Max price deviation (points)
            comment: Order comment
            
        Returns:
            TradeResult
        """
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol {symbol} not found")
            return TradeResult(
                success=False,
                order_ticket=None,
                volume=0,
                price=0,
                comment=f"Symbol {symbol} not found"
            )
        
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Failed to select {symbol}")
                return TradeResult(
                    success=False,
                    order_ticket=None,
                    volume=0,
                    price=0,
                    comment=f"Failed to select {symbol}"
                )
        
        # VALIDATE AND ROUND VOLUME
        volume_min = symbol_info.volume_min
        volume_max = symbol_info.volume_max
        volume_step = symbol_info.volume_step
        
        # Round to volume step
        volume = round(volume / volume_step) * volume_step
        
        # Check limits
        if volume < volume_min:
            logger.warning(f"Volume {volume} < min {volume_min}, using min")
            volume = volume_min
        elif volume > volume_max:
            logger.warning(f"Volume {volume} > max {volume_max}, using max")
            volume = volume_max
        
        logger.info(f"Adjusted volume: {volume} (min={volume_min}, max={volume_max}, step={volume_step})")
        
        # Get current price
        if order_type.upper() == 'BUY':
            price = mt5.symbol_info_tick(symbol).ask
            order_type_mt5 = mt5.ORDER_TYPE_BUY
        else:
            price = mt5.symbol_info_tick(symbol).bid
            order_type_mt5 = mt5.ORDER_TYPE_SELL
        
        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type_mt5,
            "price": price,
            "deviation": deviation,
            "magic": self.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Add SL/TP if provided
        if sl is not None:
            request["sl"] = sl
        if tp is not None:
            request["tp"] = tp
        
        # Send order
        logger.info(f"Sending {order_type} order: {symbol} {volume} lots @ {price:.5f}")
        
        result = mt5.order_send(request)
        
        if result is None:
            logger.error("order_send failed, result is None")
            return TradeResult(
                success=False,
                order_ticket=None,
                volume=volume,
                price=price,
                comment="order_send returned None"
            )
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.retcode} - {result.comment}")
            return TradeResult(
                success=False,
                order_ticket=result.order,
                volume=volume,
                price=price,
                comment=result.comment,
                error_code=result.retcode,
                error_description=result.comment
            )
        
        logger.info(f"[SUCCESS] Order executed: Ticket={result.order}, "
                   f"Volume={result.volume}, Price={result.price}")
        
        return TradeResult(
            success=True,
            order_ticket=result.order,
            volume=result.volume,
            price=result.price,
            comment="Order executed successfully"
        )
    
    def place_spread_orders(self,
                           gold_volume: float,
                           silver_volume: float,
                           side: str,
                           entry_zscore: float = 0.0,
                           sl_gold: Optional[float] = None,
                           tp_gold: Optional[float] = None,
                           sl_silver: Optional[float] = None,
                           tp_silver: Optional[float] = None) -> Tuple[Tuple[TradeResult, TradeResult], str]:
        """
        Place spread orders (Gold + Silver) with attribution tracking
        CRITICAL: Maintains hedge ratio after volume adjustment
        
        Args:
            gold_volume: Gold volume (lots)
            silver_volume: Silver volume (lots) - calculated from gold × hedge_ratio
            side: 'LONG' or 'SHORT'
            entry_zscore: Entry z-score for attribution tracking
            sl_gold: Gold stop loss
            tp_gold: Gold take profit
            sl_silver: Silver stop loss
            tp_silver: Silver take profit
            
        Returns:
            ((gold_result, silver_result), spread_id)
        """
        from datetime import datetime
        
        # Generate timestamp for logging/tracking
        time_now = datetime.now()
        timestamp = time_now.strftime("%Y%m%d_%H%M%S")
        short_id = time_now.strftime("%H%M%S")  # HHMMSS = 6 chars
        
        # MT5 COMMENT: Keep short for 15-char limit
        # We'll use tickets as spread_id, but comment can be anything short
        gold_comment = f"ID:{short_id}"
        silver_comment = f"ID:{short_id}"
        
        # Note: spread_id will be created AFTER orders are placed (using tickets)
        # For now, use timestamp for logging
        temp_id = timestamp
        
        # Store full setup_id for file tracking
        setup_id = getattr(self, 'current_setup_id', f"s{timestamp}")
        
        logger.info(f"Creating spread (temp: {temp_id}, setup: {setup_id}) with zscore={entry_zscore:.2f}")
        logger.info(f"  MT5 comments: '{gold_comment}' ({len(gold_comment)} chars)")
        logger.debug(f"Comments: Primary='{gold_comment}', Secondary='{silver_comment}'")
        if side.upper() == 'LONG':
            # LONG SPREAD: Buy Gold, Sell Silver
            gold_type = 'BUY'
            silver_type = 'SELL'
        elif side.upper() == 'SHORT':
            # SHORT SPREAD: Sell Gold, Buy Silver
            gold_type = 'SELL'
            silver_type = 'BUY'
        else:
            raise ValueError(f"Invalid side: {side}")
        
        # APPLY VOLUME MULTIPLIER (before any calculations)
        gold_volume_original = gold_volume
        silver_volume_original = silver_volume
        
        gold_volume *= self.volume_multiplier
        silver_volume *= self.volume_multiplier
        
        if self.volume_multiplier != 1.0:
            logger.info(f"📊 Volume Multiplier: {self.volume_multiplier}x")
            logger.info(f"   Original: Gold {gold_volume_original:.6f}, Silver {silver_volume_original:.6f}")
            logger.info(f"   Scaled:   Gold {gold_volume:.6f}, Silver {silver_volume:.6f}")
        
        # CRITICAL: Calculate hedge ratio from original volumes
        # This preserves the correct relationship between gold and silver
        hedge_ratio = silver_volume / gold_volume if gold_volume > 0 else 1.0
        
        logger.info(f"Placing {side} SPREAD orders...")
        logger.info(f"  Original: Gold {gold_volume:.6f} lots, Silver {silver_volume:.6f} lots")
        logger.info(f"  Hedge ratio (silver/gold): {hedge_ratio:.4f}")
        
        # Adjust gold volume first (rounds to MT5 step)
        gold_info = mt5.symbol_info(self.primary_symbol)
        if gold_info:
            gold_step = gold_info.volume_step
            gold_min = gold_info.volume_min
            gold_max = gold_info.volume_max
            
            # Round to step
            gold_adjusted = round(gold_volume / gold_step) * gold_step
            gold_adjusted = max(gold_min, min(gold_max, gold_adjusted))
            
            logger.info(f"  Gold adjusted: {gold_adjusted} (step={gold_step})")
        else:
            gold_adjusted = round(gold_volume, 2)
            logger.warning(f"  Could not get {self.primary_symbol} info, using {gold_adjusted}")
        
        # CRITICAL: Calculate silver volume FROM adjusted gold volume
        # This maintains the hedge ratio!
        silver_from_hedge = gold_adjusted * hedge_ratio
        
        # Now adjust silver to MT5 step
        silver_info = mt5.symbol_info(self.secondary_symbol)
        if silver_info:
            silver_step = silver_info.volume_step
            silver_min = silver_info.volume_min
            silver_max = silver_info.volume_max
            
            # Round to step
            silver_adjusted = round(silver_from_hedge / silver_step) * silver_step
            silver_adjusted = max(silver_min, min(silver_max, silver_adjusted))
            
            logger.info(f"  Silver adjusted: {silver_adjusted} (step={silver_step})")
        else:
            silver_adjusted = round(silver_from_hedge, 2)
            logger.warning(f"  Could not get {self.secondary_symbol} info, using {silver_adjusted}")
        
        # Verify final ratio
        final_ratio = silver_adjusted / gold_adjusted if gold_adjusted > 0 else 0
        ratio_error = abs(final_ratio - hedge_ratio) / hedge_ratio * 100 if hedge_ratio > 0 else 0
        
        logger.info(f"  Final volumes: Gold {gold_adjusted}, Silver {silver_adjusted}")
        logger.info(f"  Final ratio: {final_ratio:.4f} (error: {ratio_error:.2f}%)")
        
        if ratio_error > 5:
            logger.warning(f"  ⚠ Hedge ratio error {ratio_error:.2f}% > 5%!")
        
        # Place Gold order (use adjusted volume directly, skip adjustment in place_market_order)
        gold_result = self._place_order_no_adjustment(
            symbol=self.primary_symbol,
            order_type=gold_type,
            volume=gold_adjusted,
            sl=sl_gold,
            tp=tp_gold,
            comment=gold_comment
        )
        
        if not gold_result.success:
            logger.error(f"Gold order failed: {gold_result.comment}")
            return ((gold_result, TradeResult(
                success=False, order_ticket=None, volume=0, price=0,
                comment="Gold order failed, Silver order skipped"
            )), spread_id)
        
        # Place Silver order (use adjusted volume directly)
        silver_result = self._place_order_no_adjustment(
            symbol=self.secondary_symbol,
            order_type=silver_type,
            volume=silver_adjusted,
            sl=sl_silver,
            tp=tp_silver,
            comment=silver_comment
        )
        
        # Check if both orders succeeded
        if not gold_result.success or not silver_result.success:
            logger.error(f"Failed to place spread orders:")
            if not gold_result.success:
                logger.error(f"  Primary: {gold_result.comment}")
            if not silver_result.success:
                logger.error(f"  Secondary: {silver_result.comment}")
            
            # Return with None spread_id and entry_zscore
            return ((gold_result, silver_result), None, None)
        
        # CREATE SPREAD_ID FROM TICKETS (guaranteed unique and synced!)
        spread_id = f"{gold_result.order_ticket}-{silver_result.order_ticket}"
        
        logger.info(f"[MT5 SUCCESS] Spread {spread_id} filled:")
        logger.info(f"  Primary: {gold_adjusted} lots @ ${gold_result.price:.2f} (Ticket {gold_result.order_ticket})")
        logger.info(f"  Secondary: {silver_adjusted} lots @ ${silver_result.price:.4f} (Ticket {silver_result.order_ticket})")
        logger.info(f"  Entry Z-Score: {entry_zscore:.3f}")
        
        # Return tuple: (results, spread_id, entry_zscore)
        return ((gold_result, silver_result), spread_id, entry_zscore)
    
    def _place_order_no_adjustment(self,
                                   symbol: str,
                                   order_type: str,
                                   volume: float,
                                   sl: Optional[float] = None,
                                   tp: Optional[float] = None,
                                   deviation: int = 20,
                                   comment: str = "PairBot") -> TradeResult:
        """
        Place order with pre-adjusted volume (skip volume adjustment)
        Used internally by place_spread_orders
        """
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol {symbol} not found")
            return TradeResult(
                success=False, order_ticket=None, volume=0, price=0,
                comment=f"Symbol {symbol} not found"
            )
        
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Failed to select {symbol}")
                return TradeResult(
                    success=False, order_ticket=None, volume=0, price=0,
                    comment=f"Failed to select {symbol}"
                )
        
        # Get current price
        if order_type.upper() == 'BUY':
            price = mt5.symbol_info_tick(symbol).ask
            order_type_mt5 = mt5.ORDER_TYPE_BUY
        else:
            price = mt5.symbol_info_tick(symbol).bid
            order_type_mt5 = mt5.ORDER_TYPE_SELL
        
        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type_mt5,
            "price": price,
            "deviation": deviation,
            "magic": self.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Add SL/TP if provided
        if sl is not None:
            request["sl"] = sl
        if tp is not None:
            request["tp"] = tp
        
        # Send order
        logger.info(f"Sending {order_type} order: {symbol} {volume} lots @ {price:.5f}")
        
        # DEBUG: Log request details
        logger.debug(f"MT5 Request: {request}")
        
        result = mt5.order_send(request)
        
        if result is None:
            # Get last error from MT5
            error_code = mt5.last_error()
            logger.error(f"Order send failed: result is None")
            logger.error(f"MT5 last_error: {error_code}")
            
            # Check symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                logger.error(f"Symbol {symbol} info:")
                logger.error(f"  Trade mode: {symbol_info.trade_mode}")
                logger.error(f"  Trade allowed: {symbol_info.trade_mode in [mt5.SYMBOL_TRADE_MODE_FULL, mt5.SYMBOL_TRADE_MODE_LONGONLY, mt5.SYMBOL_TRADE_MODE_SHORTONLY]}")
                logger.error(f"  Volume min: {symbol_info.volume_min}")
                logger.error(f"  Volume max: {symbol_info.volume_max}")
                logger.error(f"  Volume step: {symbol_info.volume_step}")
            else:
                logger.error(f"Cannot get symbol_info for {symbol}")
            
            # Check account info
            account_info = mt5.account_info()
            if account_info:
                logger.error(f"Account info:")
                logger.error(f"  Trade allowed: {account_info.trade_allowed}")
                logger.error(f"  Trade expert: {account_info.trade_expert}")
                logger.error(f"  Balance: ${account_info.balance:,.2f}")
                logger.error(f"  Margin free: ${account_info.margin_free:,.2f}")
            
            return TradeResult(
                success=False, order_ticket=None, volume=0, price=0,
                comment=f"MT5 order_send returned None (error: {error_code})"
            )
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.retcode} - {result.comment}")
            return TradeResult(
                success=False,
                order_ticket=result.order if hasattr(result, 'order') else None,
                volume=0,
                price=0,
                comment=f"{result.retcode}: {result.comment}"
            )
        
        logger.info(f"[SUCCESS] Order executed: Ticket={result.order}, "
                   f"Volume={result.volume}, Price={result.price}")
        
        return TradeResult(
            success=True,
            order_ticket=result.order,
            volume=result.volume,
            price=result.price,
            comment="Success"
        )
    
    def close_position(self,
                      ticket: int,
                      volume: Optional[float] = None,
                      deviation: int = 20) -> TradeResult:
        """
        Close position by ticket
        
        Args:
            ticket: Position ticket
            volume: Volume to close (None = close all)
            deviation: Max price deviation
            
        Returns:
            TradeResult
        """
        # Get position info
        position = mt5.positions_get(ticket=ticket)
        
        if position is None or len(position) == 0:
            logger.error(f"Position {ticket} not found")
            return TradeResult(
                success=False,
                order_ticket=ticket,
                volume=0,
                price=0,
                comment=f"Position {ticket} not found"
            )
        
        position = position[0]
        
        # Determine close volume
        if volume is None:
            volume = position.volume
        
        # Determine close type (opposite of open)
        if position.type == mt5.POSITION_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(position.symbol).bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(position.symbol).ask
        
        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": deviation,
            "magic": self.magic_number,
            "comment": "PairBot-Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        logger.info(f"Closing position {ticket}: {position.symbol} {volume} lots @ {price:.5f}")
        
        result = mt5.order_send(request)
        
        if result is None:
            return TradeResult(
                success=False,
                order_ticket=ticket,
                volume=volume,
                price=price,
                comment="order_send returned None"
            )
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Close failed: {result.retcode} - {result.comment}")
            return TradeResult(
                success=False,
                order_ticket=ticket,
                volume=volume,
                price=price,
                comment=result.comment,
                error_code=result.retcode
            )
        
        logger.info(f"[SUCCESS] Position {ticket} closed")
        
        return TradeResult(
            success=True,
            order_ticket=result.order,
            volume=result.volume,
            price=result.price,
            comment="Position closed successfully"
        )
    
    def close_spread_positions(self,
                              gold_ticket: int,
                              silver_ticket: int) -> Tuple[TradeResult, TradeResult]:
        """
        Close spread positions
        
        Args:
            gold_ticket: Gold position ticket
            silver_ticket: Silver position ticket
            
        Returns:
            (gold_result, silver_result)
        """
        logger.info(f"Closing spread positions (Gold={gold_ticket}, Silver={silver_ticket})")
        
        gold_result = self.close_position(gold_ticket)
        silver_result = self.close_position(silver_ticket)
        
        return (gold_result, silver_result)
    
    def get_open_positions(self, symbol: Optional[str] = None) -> list:
        """
        Get all open positions
        
        Args:
            symbol: Filter by symbol (None = all)
            
        Returns:
            List of positions
        """
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        if positions is None:
            return []
        
        return list(positions)
    
    def get_position_by_ticket(self, ticket: int) -> Optional[Dict]:
        """Get position by ticket"""
        positions = mt5.positions_get(ticket=ticket)
        
        if positions is None or len(positions) == 0:
            return None
        
        pos = positions[0]
        
        return {
            'ticket': pos.ticket,
            'symbol': pos.symbol,
            'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
            'volume': pos.volume,
            'price_open': pos.price_open,
            'price_current': pos.price_current,
            'sl': pos.sl,
            'tp': pos.tp,
            'profit': pos.profit,
            'comment': pos.comment,
            'time': datetime.fromtimestamp(pos.time)
        }
    
    def modify_position(self,
                       ticket: int,
                       sl: Optional[float] = None,
                       tp: Optional[float] = None) -> TradeResult:
        """
        Modify position SL/TP
        
        Args:
            ticket: Position ticket
            sl: New stop loss
            tp: New take profit
            
        Returns:
            TradeResult
        """
        position = mt5.positions_get(ticket=ticket)
        
        if position is None or len(position) == 0:
            return TradeResult(
                success=False,
                order_ticket=ticket,
                volume=0,
                price=0,
                comment=f"Position {ticket} not found"
            )
        
        position = position[0]
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": ticket,
            "sl": sl if sl is not None else position.sl,
            "tp": tp if tp is not None else position.tp,
        }
        
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return TradeResult(
                success=False,
                order_ticket=ticket,
                volume=position.volume,
                price=position.price_open,
                comment=result.comment if result else "Modify failed"
            )
        
        logger.info(f"[SUCCESS] Position {ticket} modified (SL={sl}, TP={tp})")
        
        return TradeResult(
            success=True,
            order_ticket=ticket,
            volume=position.volume,
            price=position.price_open,
            comment="Position modified successfully"
        )
    
    def shutdown(self):
        """Shutdown MT5 connection"""
        mt5.shutdown()
        logger.info("MT5TradeExecutor shutdown")


# Convenience functions
def quick_buy(symbol: str, volume: float, sl: float = None, tp: float = None) -> TradeResult:
    """Quick buy market order"""
    executor = MT5TradeExecutor()
    result = executor.place_market_order(symbol, 'BUY', volume, sl, tp)
    executor.shutdown()
    return result


def quick_sell(symbol: str, volume: float, sl: float = None, tp: float = None) -> TradeResult:
    """Quick sell market order"""
    executor = MT5TradeExecutor()
    result = executor.place_market_order(symbol, 'SELL', volume, sl, tp)
    executor.shutdown()
    return result


def quick_close(ticket: int) -> TradeResult:
    """Quick close position"""
    executor = MT5TradeExecutor()
    result = executor.close_position(ticket)
    executor.shutdown()
    return result
