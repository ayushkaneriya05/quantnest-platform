/**
 * Portfolio Transactions - fund deposit/withdrawal history
 */
import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { 
  ArrowUpCircle, ArrowDownCircle, RefreshCw, Plus, Minus,
  DollarSign, Calendar, Clock, ShieldCheck, ShieldAlert
} from 'lucide-react';
import { portfolioApi } from '@/shared/services/portfolioApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useSetPageActions } from '@/shared/hooks/useSetPageActions';

const TYPE_STYLES = {
  DEPOSIT: { icon: ArrowUpCircle, color: 'text-green-400', bg: 'bg-green-900/20' },
  WITHDRAWAL: { icon: ArrowDownCircle, color: 'text-red-400', bg: 'bg-red-900/20' },
  ADJUSTMENT: { icon: RefreshCw, color: 'text-blue-400', bg: 'bg-blue-900/20' },
  BROKER_TRANSFER_IN: { icon: ArrowUpCircle, color: 'text-green-400', bg: 'bg-green-900/20' },
  BROKER_TRANSFER_OUT: { icon: ArrowDownCircle, color: 'text-red-400', bg: 'bg-red-900/20' },
  PROFIT_BOOKING: { icon: ArrowUpCircle, color: 'text-green-400', bg: 'bg-green-900/20' },
  LOSS_SETTLEMENT: { icon: ArrowDownCircle, color: 'text-red-400', bg: 'bg-red-900/20' },
};

export default function PortfolioTransactions() {
  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDeposit, setShowDeposit] = useState(false);
  const [showWithdraw, setShowWithdraw] = useState(false);
  const [amount, setAmount] = useState('');
  const [notes, setNotes] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portfolioData, txData] = await Promise.all([
        portfolioApi.getMyPortfolio(),
        portfolioApi.getTransactions()
      ]);
      setPortfolio(portfolioData.data);
      setTransactions(txData.data);
    } catch (error) {
      notify.error('Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Set page actions in header
  const pageActions = useMemo(() => (
    <div className="flex gap-2">
      <Button 
        onClick={() => { setShowDeposit(true); setShowWithdraw(false); }}
        className="bg-green-600 hover:bg-green-700"
        size="sm"
      >
        <Plus className="h-4 w-4 mr-1" />
        Deposit
      </Button>
      <Button 
        onClick={() => { setShowWithdraw(true); setShowDeposit(false); }}
        variant="outline"
        className="border-red-800 text-red-400"
        size="sm"
      >
        <Minus className="h-4 w-4 mr-1" />
        Withdraw
      </Button>
    </div>
  ), []);

  useSetPageActions(pageActions);

  const handleDeposit = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      notify.error('Enter a valid amount');
      return;
    }
    try {
      await portfolioApi.deposit(portfolio.id, parseFloat(amount), notes);
      notify.success(`₹${amount} deposited successfully`);
      setShowDeposit(false);
      setAmount('');
      setNotes('');
      fetchData();
    } catch (error) {
      notify.error('Deposit failed');
    }
  };

  const handleWithdraw = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      notify.error('Enter a valid amount');
      return;
    }
    if (parseFloat(amount) > portfolio.current_capital) {
      notify.error('Insufficient funds');
      return;
    }
    try {
      await portfolioApi.withdraw(portfolio.id, parseFloat(amount), notes);
      notify.success(`₹${amount} withdrawn successfully`);
      setShowWithdraw(false);
      setAmount('');
      setNotes('');
      fetchData();
    } catch (error) {
      notify.error('Withdrawal failed');
    }
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', currency: 'INR', maximumFractionDigits: 0 
    }).format(Math.abs(val || 0));
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Balance Card */}
      <Card className="bg-gradient-to-r from-indigo-900/50 to-purple-900/50 border-indigo-800/50">
        <CardContent className="py-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-indigo-300">Available Balance</p>
              <p className="text-3xl font-bold text-white mt-1">
                {formatCurrency(portfolio?.current_capital)}
              </p>
            </div>
            <DollarSign className="h-12 w-12 text-indigo-400/50" />
          </div>
        </CardContent>
      </Card>

      {/* Deposit/Withdraw Form */}
      {(showDeposit || showWithdraw) && (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className={showDeposit ? 'text-green-400' : 'text-red-400'}>
              {showDeposit ? 'Deposit Funds' : 'Withdraw Funds'}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-gray-400 text-sm">Amount (₹)</label>
                <Input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="Enter amount"
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <label className="text-gray-400 text-sm">Notes (optional)</label>
                <Input
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add a note"
                  className="bg-gray-800 border-gray-700 text-white"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button 
                variant="outline" 
                onClick={() => { setShowDeposit(false); setShowWithdraw(false); }}
                className="border-gray-700"
              >
                Cancel
              </Button>
              <Button 
                onClick={showDeposit ? handleDeposit : handleWithdraw}
                className={showDeposit ? 'bg-green-600' : 'bg-red-600'}
              >
                {showDeposit ? 'Deposit' : 'Withdraw'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Transactions List */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Transaction History</CardTitle>
        </CardHeader>
        <CardContent>
          {transactions.length === 0 ? (
            <div className="text-center py-8">
              <Clock className="h-10 w-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">No transactions yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {transactions.map((tx) => {
                const style = TYPE_STYLES[tx.transaction_type] || TYPE_STYLES.ADJUSTMENT;
                const Icon = style.icon;
                return (
                  <div 
                    key={tx.id}
                    className={`flex items-center justify-between p-4 rounded-lg ${style.bg}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg ${style.bg}`}>
                        <Icon className={`h-5 w-5 ${style.color}`} />
                      </div>
                      <div>
                        <p className="text-white font-medium">
                          {tx.transaction_type.replace(/_/g, ' ')}
                        </p>
                        <p className="text-sm text-gray-400">
                          {formatDate(tx.created_at)}
                        </p>
                        {tx.notes && (
                          <p className="text-xs text-gray-500 mt-1">{tx.notes}</p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${tx.amount > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {tx.amount > 0 ? '+' : '-'}{formatCurrency(tx.amount)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatCurrency(tx.balance_before)} → {formatCurrency(tx.balance_after)}
                      </p>
                      {tx.requires_approval && (
                        <Badge className={`text-[10px] mt-1 ${tx.is_approved ? 'bg-emerald-600/20 text-emerald-400' : 'bg-amber-600/20 text-amber-400'}`}>
                          {tx.is_approved ? 'Approved' : 'Pending Approval'}
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
