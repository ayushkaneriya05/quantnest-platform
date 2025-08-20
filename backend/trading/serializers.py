from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from .models import Instrument, Watchlist, Account, Position, Order, TradeHistory

class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = ['id', 'symbol', 'company_name']

class WatchlistSerializer(serializers.ModelSerializer):
    instruments = InstrumentSerializer(many=True, read_only=True)

    class Meta:
        model = Watchlist
        fields = ['id', 'user', 'instruments']

class AccountSerializer(serializers.ModelSerializer):
    available_balance = serializers.SerializerMethodField()
    total_portfolio_value = serializers.SerializerMethodField()
    total_pnl = serializers.SerializerMethodField()
    margin_used = serializers.SerializerMethodField()
    buying_power = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = [
            'id', 'user', 'balance', 'margin', 'available_balance', 
            'total_portfolio_value', 'total_pnl', 'margin_used', 'buying_power'
        ]
        
    def get_available_balance(self, obj):
        """Calculate available balance after margin requirements"""
        margin_used = self.get_margin_used(obj)
        return max(0, obj.balance - margin_used)
    
    def get_total_portfolio_value(self, obj):
        """Calculate total portfolio value including positions"""
        total_value = obj.balance
        positions = obj.positions.all()
        
        for position in positions:
            # Mock current price calculation - in production, get from market data
            current_price = position.average_price * (1 + 0.02)  # Mock 2% gain
            position_value = position.quantity * current_price
            total_value += position_value - (position.average_price * abs(position.quantity))
            
        return total_value
    
    def get_total_pnl(self, obj):
        """Calculate total profit/loss across all positions"""
        total_pnl = Decimal('0.00')
        positions = obj.positions.all()
        
        for position in positions:
            # Mock current price - in production, get from market data
            current_price = Decimal(str(position.average_price * (1 + 0.02)))
            position_pnl = (current_price - position.average_price) * position.quantity
            total_pnl += position_pnl
            
        return total_pnl
    
    def get_margin_used(self, obj):
        """Calculate margin used for positions"""
        margin_used = Decimal('0.00')
        positions = obj.positions.all()
        
        for position in positions:
            # For short positions, require higher margin
            margin_rate = Decimal('0.5') if position.quantity < 0 else Decimal('0.2')  # 50% for short, 20% for long
            position_value = abs(position.quantity) * position.average_price
            margin_used += position_value * margin_rate
            
        return margin_used
    
    def get_buying_power(self, obj):
        """Calculate buying power based on available balance and margin"""
        available_balance = self.get_available_balance(obj)
        # Assume 5x leverage for simplicity
        return available_balance * 5

class PositionSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(read_only=True)
    current_price = serializers.SerializerMethodField()
    market_value = serializers.SerializerMethodField()
    pnl = serializers.SerializerMethodField()
    pnl_percentage = serializers.SerializerMethodField()
    position_type = serializers.SerializerMethodField()
    
    class Meta:
        model = Position
        fields = [
            'id', 'instrument', 'quantity', 'average_price', 'current_price',
            'market_value', 'pnl', 'pnl_percentage', 'position_type'
        ]
    
    def get_current_price(self, obj):
        """Get current market price - mock for demo"""
        # In production, this would fetch from market data service
        return obj.average_price * (1 + 0.02)  # Mock 2% change
    
    def get_market_value(self, obj):
        """Calculate current market value of position"""
        current_price = self.get_current_price(obj)
        return abs(obj.quantity) * current_price
    
    def get_pnl(self, obj):
        """Calculate profit/loss for position"""
        current_price = self.get_current_price(obj)
        return (current_price - obj.average_price) * obj.quantity
    
    def get_pnl_percentage(self, obj):
        """Calculate profit/loss percentage"""
        pnl = self.get_pnl(obj)
        invested_value = abs(obj.quantity) * obj.average_price
        if invested_value > 0:
            return (pnl / invested_value) * 100
        return 0
    
    def get_position_type(self, obj):
        """Determine if position is long or short"""
        return "LONG" if obj.quantity > 0 else "SHORT"

class OrderSerializer(serializers.ModelSerializer):
    instrument_id = serializers.IntegerField(write_only=True, required=False)
    instrument_symbol = serializers.CharField(write_only=True, required=False)
    instrument = InstrumentSerializer(read_only=True)
    estimated_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'instrument', 'instrument_id', 'instrument_symbol', 'order_type', 'status', 
            'transaction_type', 'quantity', 'price', 'trigger_price', 'created_at', 'executed_at',
            'estimated_value'
        ]
        read_only_fields = ['id', 'instrument', 'status', 'created_at', 'executed_at']

    def get_estimated_value(self, obj):
        """Calculate estimated order value"""
        if obj.order_type == 'MARKET':
            # For market orders, use current market price (mock)
            price = obj.instrument.symbol  # This would be current market price
            return obj.quantity * 2500  # Mock price
        elif obj.price:
            return obj.quantity * obj.price
        return 0

    def validate(self, data):
        """Comprehensive order validation including short selling checks"""
        order_type = data.get('order_type')
        transaction_type = data.get('transaction_type')
        quantity = data.get('quantity')
        price = data.get('price')
        trigger_price = data.get('trigger_price')
        
        # Validate required fields based on order type
        if order_type in ['LIMIT', 'STOP_LIMIT'] and not price:
            raise serializers.ValidationError("Price is required for limit orders")
        
        if order_type in ['STOP', 'STOP_LIMIT'] and not trigger_price:
            raise serializers.ValidationError("Trigger price is required for stop orders")
        
        # Validate quantity
        if quantity <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        
        # Validate price values
        if price and price <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        
        if trigger_price and trigger_price <= 0:
            raise serializers.ValidationError("Trigger price must be greater than 0")
        
        return data

    def create(self, validated_data):
        """Create order with comprehensive validation and short selling logic"""
        user = self.context['request'].user
        account, _ = Account.objects.get_or_create(user=user)
        
        # Get instrument
        instrument = None
        if 'instrument_id' in validated_data:
            instrument_id = validated_data.pop('instrument_id')
            try:
                instrument = Instrument.objects.get(id=instrument_id)
            except Instrument.DoesNotExist:
                raise serializers.ValidationError("Instrument not found")
        elif 'instrument_symbol' in validated_data:
            instrument_symbol = validated_data.pop('instrument_symbol')
            try:
                instrument = Instrument.objects.get(symbol=instrument_symbol)
            except Instrument.DoesNotExist:
                raise serializers.ValidationError(f"Instrument with symbol {instrument_symbol} not found")
        else:
            raise serializers.ValidationError("Either instrument_id or instrument_symbol is required")
        
        transaction_type = validated_data['transaction_type']
        quantity = validated_data['quantity']
        order_type = validated_data['order_type']
        
        # Calculate order value for balance/margin checks
        if order_type == 'MARKET':
            # Use mock current price for market orders
            estimated_price = 2500  # Mock price
        else:
            estimated_price = validated_data.get('price', 2500)
        
        order_value = quantity * estimated_price
        
        # Check for short selling validation
        if transaction_type == 'SELL':
            try:
                position = Position.objects.get(account=account, instrument=instrument)
                available_quantity = position.quantity
                
                # Allow short selling if user doesn't have position or wants to sell more than they have
                if available_quantity < quantity:
                    short_quantity = quantity - max(0, available_quantity)
                    
                    # Calculate margin requirement for short selling (higher margin)
                    short_margin_required = short_quantity * estimated_price * Decimal('0.5')  # 50% margin for short
                    
                    if account.balance < short_margin_required:
                        raise serializers.ValidationError(
                            f"Insufficient margin for short selling. Required: ₹{short_margin_required}, "
                            f"Available: ₹{account.balance}"
                        )
                
            except Position.DoesNotExist:
                # No existing position - this is a pure short sell
                short_margin_required = order_value * Decimal('0.5')  # 50% margin
                
                if account.balance < short_margin_required:
                    raise serializers.ValidationError(
                        f"Insufficient margin for short selling. Required: ₹{short_margin_required}, "
                        f"Available: ₹{account.balance}"
                    )
        
        # For buy orders, check if sufficient balance
        elif transaction_type == 'BUY':
            margin_required = order_value * Decimal('0.2')  # 20% margin for long positions
            
            if account.balance < margin_required:
                raise serializers.ValidationError(
                    f"Insufficient balance. Required: ₹{margin_required}, "
                    f"Available: ₹{account.balance}"
                )
        
        # Create the order
        with transaction.atomic():
            order = Order.objects.create(
                account=account,
                instrument=instrument,
                **validated_data
            )
            
            # For market orders, execute immediately (simplified for demo)
            if order_type == 'MARKET':
                self._execute_order(order, estimated_price)
        
        return order
    
    def _execute_order(self, order, execution_price):
        """Execute market order immediately"""
        with transaction.atomic():
            # Update order status
            order.status = 'EXECUTED'
            order.executed_at = timezone.now()
            order.save()
            
            # Create trade history record
            TradeHistory.objects.create(
                order=order,
                executed_price=execution_price,
                quantity=order.quantity
            )
            
            # Update position
            self._update_position(order, execution_price)
            
            # Update account balance
            self._update_account_balance(order, execution_price)
    
    def _update_position(self, order, execution_price):
        """Update or create position based on executed order"""
        account = order.account
        instrument = order.instrument
        
        try:
            position = Position.objects.get(account=account, instrument=instrument)
            
            if order.transaction_type == 'BUY':
                # Add to position
                total_cost = (position.quantity * position.average_price) + (order.quantity * execution_price)
                total_quantity = position.quantity + order.quantity
                
                if total_quantity != 0:
                    position.average_price = total_cost / total_quantity
                    position.quantity = total_quantity
                else:
                    position.delete()
                    return
                    
            else:  # SELL
                position.quantity -= order.quantity
                
                # If position becomes zero or changes direction, handle accordingly
                if position.quantity == 0:
                    position.delete()
                    return
                elif position.quantity < 0:
                    # Position has gone short - update average price for short position
                    position.average_price = execution_price
            
            position.save()
            
        except Position.DoesNotExist:
            # Create new position
            if order.transaction_type == 'BUY':
                quantity = order.quantity
            else:  # SELL - creating short position
                quantity = -order.quantity
            
            Position.objects.create(
                account=account,
                instrument=instrument,
                quantity=quantity,
                average_price=execution_price
            )
    
    def _update_account_balance(self, order, execution_price):
        """Update account balance based on executed order"""
        account = order.account
        order_value = order.quantity * execution_price
        
        if order.transaction_type == 'BUY':
            # Deduct cost from balance
            account.balance -= order_value
        else:  # SELL
            # Add proceeds to balance
            account.balance += order_value
        
        account.save()

class TradeHistorySerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    instrument_symbol = serializers.CharField(source='order.instrument.symbol', read_only=True)
    transaction_type = serializers.CharField(source='order.transaction_type', read_only=True)
    
    class Meta:
        model = TradeHistory
        fields = [
            'id', 'order', 'instrument_symbol', 'transaction_type', 
            'executed_price', 'quantity', 'timestamp'
        ]

# Import timezone at the top of the file
from django.utils import timezone
