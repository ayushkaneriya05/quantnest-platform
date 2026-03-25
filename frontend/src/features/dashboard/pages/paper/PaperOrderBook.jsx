/**
 * Paper Order Book - place and manage orders
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { 
  ChevronLeft, Play, X, Clock, CheckCircle, XCircle
} from 'lucide-react';
import { paperApi } from '@/shared/services/paperApi';
import { instrumentsApi } from '@/shared/services/instrumentsApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useSetPageActions } from '@/shared/hooks/useSetPageActions';

const ORDER_STATUS_STYLES = {
  PENDING: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-600' },
  PLACED: { icon: Clock, color: 'text-blue-400', bg: 'bg-blue-600' },
  FILLED: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-600' },
  CANCELLED: { icon: XCircle, color: 'text-gray-400', bg: 'bg-gray-600' },
  REJECTED: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-600' },
};

export default function PaperOrderBook() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [orders, setOrders] = useState([]);
  const [instruments, setInstruments] = useState([]);
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  
  const [formData, setFormData] = useState({
    instrument: '',
    order_type: 'MARKET',
    product_type: 'MIS',
    side: 'BUY',
    quantity: 1,
    price: '',
    trigger_price: '',
  });

  const fetchData = async () => {
    try {
      const [ordersData, instrumentsData, accData] = await Promise.all([
        paperApi.getOrders(),
        instrumentsApi.getAll(),
        paperApi.getActiveAccount()
      ]);
      setOrders(ordersData.data);
      setInstruments(instrumentsData.data.slice(0, 100)); // Limit for performance
      setAccount(accData.data);
    } catch (error) {
      notify.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Set page actions in header
  const pageActions = useMemo(() => (
    <Button 
      onClick={() => setShowForm(prev => !prev)}
      className="bg-indigo-600 hover:bg-indigo-700"
      size="sm"
    >
      <Play className="h-4 w-4 mr-1" />
      New Order
    </Button>
  ), []);

  useSetPageActions(pageActions);

  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    if (!formData.instrument || !account) {
      notify.error('Select an instrument');
      return;
    }
    
    try {
      const data = {
        account: account.id,
        instrument: parseInt(formData.instrument),
        order_type: formData.order_type,
        product_type: formData.product_type,
        side: formData.side,
        quantity: parseInt(formData.quantity),
        price: formData.price ? parseFloat(formData.price) : null,
        trigger_price: formData.trigger_price ? parseFloat(formData.trigger_price) : null,
      };
      
      await paperApi.placeOrder(data);
      notify.success('Order placed successfully');
      setShowForm(false);
      setFormData({
        instrument: '',
        order_type: 'MARKET',
        product_type: 'MIS',
        side: 'BUY',
        quantity: 1,
        price: '',
        trigger_price: '',
      });
      fetchData();
    } catch (error) {
      notify.error('Failed to place order');
    }
  };

  const handleCancel = async (orderId) => {
    try {
      await paperApi.cancelOrder(orderId);
      notify.success('Order cancelled');
      fetchData();
    } catch (error) {
      notify.error('Failed to cancel order');
    }
  };

  const formatTime = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  const pendingOrders = orders.filter(o => ['PENDING', 'PLACED'].includes(o.status));
  const completedOrders = orders.filter(o => !['PENDING', 'PLACED'].includes(o.status));

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Order Form */}
      {showForm && (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Place Order</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePlaceOrder} className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-2 col-span-2">
                  <Label className="text-gray-400">Instrument *</Label>
                  <Select 
                    value={formData.instrument} 
                    onValueChange={(v) => setFormData({ ...formData, instrument: v })}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue placeholder="Search instrument" />
                    </SelectTrigger>
                    <SelectContent>
                      {instruments.map(i => (
                        <SelectItem key={i.id} value={i.id.toString()}>{i.symbol} - {i.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-400">Side</Label>
                  <Select 
                    value={formData.side} 
                    onValueChange={(v) => setFormData({ ...formData, side: v })}
                  >
                    <SelectTrigger className={`${formData.side === 'BUY' ? 'bg-green-900/30 border-green-800' : 'bg-red-900/30 border-red-800'}`}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="BUY">BUY</SelectItem>
                      <SelectItem value="SELL">SELL</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-400">Order Type</Label>
                  <Select 
                    value={formData.order_type} 
                    onValueChange={(v) => setFormData({ ...formData, order_type: v })}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MARKET">Market</SelectItem>
                      <SelectItem value="LIMIT">Limit</SelectItem>
                      <SelectItem value="STOP_LIMIT">Stop Limit</SelectItem>
                      <SelectItem value="STOP_MARKET">Stop Market</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-2">
                  <Label className="text-gray-400">Quantity *</Label>
                  <Input
                    type="number"
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    min="1"
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>
                {['LIMIT', 'STOP_LIMIT'].includes(formData.order_type) && (
                  <div className="space-y-2">
                    <Label className="text-gray-400">Price</Label>
                    <Input
                      type="number"
                      step="0.05"
                      value={formData.price}
                      onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                      className="bg-gray-800 border-gray-700 text-white"
                    />
                  </div>
                )}
                {['STOP_LIMIT', 'STOP_MARKET'].includes(formData.order_type) && (
                  <div className="space-y-2">
                    <Label className="text-gray-400">Trigger Price</Label>
                    <Input
                      type="number"
                      step="0.05"
                      value={formData.trigger_price}
                      onChange={(e) => setFormData({ ...formData, trigger_price: e.target.value })}
                      className="bg-gray-800 border-gray-700 text-white"
                    />
                  </div>
                )}
                <div className="space-y-2">
                  <Label className="text-gray-400">Product</Label>
                  <Select 
                    value={formData.product_type} 
                    onValueChange={(v) => setFormData({ ...formData, product_type: v })}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MIS">MIS (Intraday)</SelectItem>
                      <SelectItem value="CNC">CNC (Delivery)</SelectItem>
                      <SelectItem value="NRML">NRML (F&O)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setShowForm(false)} className="border-gray-700">
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className={formData.side === 'BUY' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
                >
                  <Play className="h-4 w-4 mr-1" />
                  {formData.side} Order
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Pending Orders */}
      {pendingOrders.length > 0 && (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Pending Orders</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr className="text-left text-xs text-gray-400">
                  <th className="p-3">Time</th>
                  <th className="p-3">Symbol</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Side</th>
                  <th className="p-3">Qty</th>
                  <th className="p-3">Price</th>
                  <th className="p-3">Status</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {pendingOrders.map((order) => (
                  <tr key={order.id} className="border-t border-gray-800">
                    <td className="p-3 text-gray-300">{formatTime(order.placed_at)}</td>
                    <td className="p-3 text-white font-medium">{order.instrument_symbol}</td>
                    <td className="p-3 text-gray-300">{order.order_type}</td>
                    <td className="p-3">
                      <Badge className={order.side === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                        {order.side}
                      </Badge>
                    </td>
                    <td className="p-3 text-white">{order.quantity}</td>
                    <td className="p-3 text-white">{order.price ? `₹${parseFloat(order.price).toFixed(2)}` : 'Market'}</td>
                    <td className="p-3">
                      <Badge className={ORDER_STATUS_STYLES[order.status]?.bg}>
                        {order.status}
                      </Badge>
                    </td>
                    <td className="p-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCancel(order.id)}
                        className="text-red-400"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Order History */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Order History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {completedOrders.length === 0 ? (
            <div className="p-6 text-center text-gray-500">No order history</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr className="text-left text-xs text-gray-400">
                  <th className="p-3">Time</th>
                  <th className="p-3">Symbol</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Side</th>
                  <th className="p-3">Qty</th>
                  <th className="p-3">Fill Price</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {completedOrders.slice(0, 20).map((order) => (
                  <tr key={order.id} className="border-t border-gray-800">
                    <td className="p-3 text-gray-300">{formatTime(order.executed_at || order.placed_at)}</td>
                    <td className="p-3 text-white font-medium">{order.instrument_symbol}</td>
                    <td className="p-3 text-gray-300">{order.order_type}</td>
                    <td className="p-3">
                      <Badge className={order.side === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                        {order.side}
                      </Badge>
                    </td>
                    <td className="p-3 text-white">{order.filled_quantity}/{order.quantity}</td>
                    <td className="p-3 text-white">
                      {order.avg_fill_price ? `₹${parseFloat(order.avg_fill_price).toFixed(2)}` : '-'}
                    </td>
                    <td className="p-3">
                      <Badge className={ORDER_STATUS_STYLES[order.status]?.bg}>
                        {order.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
