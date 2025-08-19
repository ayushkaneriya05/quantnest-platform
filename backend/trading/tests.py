# backend/trading/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Instrument, Account, Order, Position
from decimal import Decimal

User = get_user_model()

class TradingAPITests(APITestCase):
    def setUp(self):
        """Set up the environment for each test."""
        self.user = User.objects.create_user(email='test@example.com', password='strongpassword', username='testuser')
        self.instrument = Instrument.objects.create(symbol='RELIANCE', company_name='Reliance Industries')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.account, _ = Account.objects.get_or_create(user=self.user, defaults={'balance': Decimal('100000.00')})

    def test_create_market_order_success(self):
        """Ensure a user can place a valid market order."""
        url = '/api/v1/trading/orders/'
        data = {
            'instrument_symbol': 'RELIANCE',
            'order_type': 'MARKET',
            'transaction_type': 'BUY',
            'quantity': 10
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().instrument, self.instrument)
        self.assertEqual(Order.objects.get().status, 'OPEN')

    def test_create_order_invalid_symbol(self):
        """Test creating an order for a non-existent symbol."""
        url = '/api/v1/trading/orders/'
        data = {'instrument_symbol': 'FAKESYMBOL', 'order_type': 'MARKET', 'transaction_type': 'BUY', 'quantity': 10}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_open_order(self):
        """Ensure a user can cancel an order that is still open."""
        order = Order.objects.create(
            account=self.account,
            instrument=self.instrument,
            order_type='LIMIT',
            transaction_type='BUY',
            quantity=5,
            price='2000.00',
            status='OPEN'
        )
        url = f'/api/v1/trading/orders/{order.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        order.refresh_from_db()
        self.assertEqual(order.status, 'CANCELLED')

    def test_cannot_cancel_executed_order(self):
        """Ensure a user cannot cancel an already executed order."""
        order = Order.objects.create(
            account=self.account,
            instrument=self.instrument,
            order_type='MARKET',
            transaction_type='BUY',
            quantity=5,
            status='EXECUTED' # This order is already filled
        )
        url = f'/api/v1/trading/orders/{order.id}/'
        response = self.client.delete(url)
        # We expect a 404 because the queryset in the view only includes 'OPEN' orders
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_positions_and_account(self):
        """Test retrieving a user's positions and account details."""
        Position.objects.create(
            account=self.account,
            instrument=self.instrument,
            quantity=100,
            average_price='2500.00'
        )
        
        # Test positions endpoint
        positions_url = '/api/v1/trading/positions/'
        pos_response = self.client.get(positions_url)
        self.assertEqual(pos_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(pos_response.data), 1)
        self.assertEqual(pos_response.data[0]['instrument']['symbol'], 'RELIANCE')
        
        # Test account endpoint
        account_url = '/api/v1/trading/account/'
        acc_response = self.client.get(account_url)
        self.assertEqual(acc_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(acc_response.data['balance']), self.account.balance)