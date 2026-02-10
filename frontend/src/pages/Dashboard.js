import React, { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { 
  TrendingUp, 
  TrendingDown, 
  Wallet,
  Target,
  Plus,
  ArrowRight,
  RefreshCw,
  Flag
} from "lucide-react";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  CartesianGrid
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Progress } from "../components/ui/progress";
import { PageHeader } from "../components/layout/PageHeader";
import { TransactionDrawer } from "../components/transactions/TransactionDrawer";
import { useAuth } from "../contexts/AuthContext";
import { useData } from "../contexts/DataContext";
import { formatCurrency, getCurrentMonth, formatShortDate, getMemberColor } from "../lib/utils";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const { onMenuClick } = useOutletContext();
  const { api, user } = useAuth();
  const { members, getCategoryById, getMemberById, goals, accounts } = useData();
  
  const [month, setMonth] = useState(getCurrentMonth());
  const [summary, setSummary] = useState({ income: 0, expenses: 0, net: 0, budget: 0, to_budget: 0 });
  const [spendingData, setSpendingData] = useState({ current: [], previous: [] });
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [recurring, setRecurring] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerType, setDrawerType] = useState("expense");

  useEffect(() => {
    fetchDashboardData();
  }, [month]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [summaryRes, chartRes, txRes, recRes] = await Promise.all([
        api.get(`/dashboard/summary?month=${month}`),
        api.get(`/dashboard/spending-chart?month=${month}`),
        api.get(`/transactions?month=${month}`),
        api.get("/recurring"),
      ]);
      
      setSummary(summaryRes.data);
      setSpendingData(chartRes.data);
      setRecentTransactions(txRes.data.slice(0, 8));
      setRecurring(recRes.data.filter(r => r.next_date.startsWith(month)).slice(0, 6));
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const openAddIncome = () => {
    setDrawerType("income");
    setDrawerOpen(true);
  };

  const openAddExpense = () => {
    setDrawerType("expense");
    setDrawerOpen(true);
  };

  const chartData = spendingData.current.map((item, idx) => ({
    day: item.day,
    current: item.amount,
    previous: spendingData.previous[idx]?.amount || 0,
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="text-sm font-medium">Day {label}</p>
          <p className="text-sm text-accent">This month: {formatCurrency(payload[0]?.value || 0)}</p>
          <p className="text-sm text-muted-foreground">Last month: {formatCurrency(payload[1]?.value || 0)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        title={`Welcome back, ${user?.name || "User"}`}
        subtitle="Here's your financial overview"
        month={month}
        setMonth={setMonth}
        onMenuClick={onMenuClick}
        actions={
          <Button onClick={openAddExpense} data-testid="add-transaction-btn">
            <Plus className="w-4 h-4 mr-2" />
            Add Transaction
          </Button>
        }
      />

      <div className="page-content space-y-6">
        {/* Summary Cards */}
        <div className="summary-grid">
          <Card className="card-hover" data-testid="income-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Income</CardTitle>
              <TrendingUp className="w-4 h-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                {formatCurrency(summary.income)}
              </div>
              <button
                onClick={openAddIncome}
                className="text-xs text-accent hover:underline mt-1 flex items-center gap-1"
                data-testid="add-income-link"
              >
                <Plus className="w-3 h-3" /> Add Income
              </button>
            </CardContent>
          </Card>

          <Card className="card-hover" data-testid="expenses-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Expenses</CardTitle>
              <TrendingDown className="w-4 h-4 text-rose-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tabular-nums">
                {formatCurrency(summary.expenses)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">This month</p>
            </CardContent>
          </Card>

          <Card className="card-hover" data-testid="budget-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">To Budget</CardTitle>
              <Target className="w-4 h-4 text-accent" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold tabular-nums ${summary.to_budget >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                {formatCurrency(summary.to_budget)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {summary.to_budget >= 0 ? "Remaining" : "Over budget"}
              </p>
            </CardContent>
          </Card>

          <Card className="card-hover" data-testid="net-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Net Position</CardTitle>
              <Wallet className="w-4 h-4 text-accent" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold tabular-nums ${summary.net >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                {formatCurrency(summary.net)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Income - Expenses</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Grid */}
        <div className="dashboard-grid">
          {/* Spending Chart */}
          <Card data-testid="spending-chart-card">
            <CardHeader>
              <CardTitle className="text-lg">Spending This Month vs Last Month</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis 
                      dataKey="day" 
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={12}
                      tickLine={false}
                    />
                    <YAxis 
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={12}
                      tickLine={false}
                      tickFormatter={(value) => `$${value}`}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Line 
                      type="monotone" 
                      dataKey="current" 
                      stroke="hsl(var(--accent))" 
                      strokeWidth={2}
                      dot={false}
                      name="This Month"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="previous" 
                      stroke="hsl(var(--muted-foreground))" 
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      dot={false}
                      name="Last Month"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Recent Transactions */}
            <Card data-testid="recent-transactions-card">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-lg">Recent Transactions</CardTitle>
                <Link to="/transactions" className="text-sm text-accent hover:underline flex items-center gap-1">
                  View all <ArrowRight className="w-3 h-3" />
                </Link>
              </CardHeader>
              <CardContent className="p-0">
                {recentTransactions.length === 0 ? (
                  <div className="p-6 text-center text-muted-foreground">
                    No transactions this month
                  </div>
                ) : (
                  <div className="divide-y divide-border">
                    {recentTransactions.map((tx) => {
                      const member = getMemberById(tx.member_id);
                      const category = getCategoryById(tx.category_id);
                      const memberColors = getMemberColor(member?.name);
                      
                      return (
                        <div key={tx.id} className="px-4 py-3 flex items-center justify-between">
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="flex flex-col min-w-0">
                              <span className="font-medium truncate">{tx.merchant_name || "Transaction"}</span>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span>{category?.category_name || "Uncategorized"}</span>
                                {member && (
                                  <span className={`px-1.5 py-0.5 rounded ${memberColors.bg} ${memberColors.text}`}>
                                    {member.name}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className={`font-medium tabular-nums ${tx.amount >= 0 ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>
                            {formatCurrency(tx.amount)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Upcoming Recurring */}
            <Card data-testid="upcoming-recurring-card">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-lg">Upcoming Recurring</CardTitle>
                <Link to="/recurring" className="text-sm text-accent hover:underline flex items-center gap-1">
                  View all <ArrowRight className="w-3 h-3" />
                </Link>
              </CardHeader>
              <CardContent className="p-0">
                {recurring.length === 0 ? (
                  <div className="p-6 text-center text-muted-foreground">
                    No recurring items due
                  </div>
                ) : (
                  <div className="divide-y divide-border">
                    {recurring.map((item) => (
                      <div key={item.id} className="px-4 py-3 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <RefreshCw className="w-4 h-4 text-muted-foreground" />
                          <div>
                            <span className="font-medium">{item.name}</span>
                            <p className="text-xs text-muted-foreground">
                              Due {formatShortDate(item.next_date)}
                            </p>
                          </div>
                        </div>
                        <span className={`font-medium tabular-nums ${item.type === 'income' ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>
                          {formatCurrency(item.amount)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Goals */}
        <Card data-testid="goals-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Goals</CardTitle>
            <Link to="/goals" className="text-sm text-accent hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </CardHeader>
          <CardContent>
            {goals.length === 0 ? (
              <div className="text-center text-muted-foreground py-4">
                No goals yet. Create one to start saving!
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {goals.slice(0, 3).map((goal) => {
                  const progress = (goal.current_amount / goal.target_amount) * 100;
                  return (
                    <div 
                      key={goal.id} 
                      className="p-4 rounded-xl border border-border bg-secondary/30"
                    >
                      <div className="flex items-center gap-3 mb-3">
                        <div 
                          className="w-10 h-10 rounded-lg flex items-center justify-center"
                          style={{ backgroundColor: `${goal.color}20` }}
                        >
                          <Flag className="w-5 h-5" style={{ color: goal.color }} />
                        </div>
                        <div>
                          <h4 className="font-medium">{goal.name}</h4>
                          <p className="text-xs text-muted-foreground">
                            {formatCurrency(goal.current_amount)} of {formatCurrency(goal.target_amount)}
                          </p>
                        </div>
                      </div>
                      <Progress 
                        value={Math.min(progress, 100)} 
                        className="h-2"
                        style={{ '--progress-color': goal.color }}
                      />
                      <p className="text-xs text-muted-foreground mt-2">
                        {progress.toFixed(0)}% complete
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <TransactionDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        defaultType={drawerType}
        onSave={fetchDashboardData}
      />
    </div>
  );
}
