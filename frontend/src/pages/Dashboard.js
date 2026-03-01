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
  Flag,
  ArrowUpRight,
  ArrowDownRight
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
  const { members, getCategoryById, getMemberById, goals } = useData();
  
  const [month, setMonth] = useState(getCurrentMonth());
  const [summary, setSummary] = useState({ 
    income: 0, expenses: 0, net: 0, budget: 0, to_budget: 0,
    prev_income: 0, prev_expenses: 0, income_change: 0, expenses_change: 0
  });
  const [spendingData, setSpendingData] = useState({ current: [], previous: [] });
  const [categorySpending, setCategorySpending] = useState({ categories: [], total: 0 });
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
      const [summaryRes, chartRes, catSpendingRes, txRes, recRes] = await Promise.all([
        api.get(`/dashboard/summary?month=${month}`),
        api.get(`/dashboard/spending-chart?month=${month}`),
        api.get(`/dashboard/category-spending?month=${month}`),
        api.get(`/transactions?month=${month}`),
        api.get("/recurring"),
      ]);
      
      setSummary(summaryRes.data);
      setSpendingData(chartRes.data);
      setCategorySpending(catSpendingRes.data);
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
        <div className="bg-card border border-border rounded-lg shadow-lg p-3">
          <p className="text-sm font-medium">Day {label}</p>
          <p className="text-sm text-blue-500">This month: {formatCurrency(payload[0]?.value || 0)}</p>
          <p className="text-sm text-muted-foreground">Last month: {formatCurrency(payload[1]?.value || 0)}</p>
        </div>
      );
    }
    return null;
  };

  const formatChange = (current, previous) => {
    if (previous === 0) return null;
    const change = ((current - previous) / previous * 100).toFixed(0);
    return change;
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
          <Card className="card-hover bg-gradient-to-br from-emerald-50 to-teal-100/50 border-emerald-200/60 dark:from-emerald-900/30 dark:to-teal-900/20 dark:border-emerald-700/30" data-testid="income-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-emerald-700 dark:text-emerald-300">Income</CardTitle>
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300 tabular-nums">
                {formatCurrency(summary.income)}
              </div>
              <div className="flex items-center justify-between mt-1">
                <button
                  onClick={openAddIncome}
                  className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1"
                  data-testid="add-income-link"
                >
                  <Plus className="w-3 h-3" /> Add Income
                </button>
                {summary.income_change !== 0 && (
                  <span className={`text-xs flex items-center gap-0.5 ${
                    summary.income_change > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'
                  }`}>
                    {summary.income_change > 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                    {formatChange(summary.income, summary.prev_income)}% vs last month
                  </span>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover bg-gradient-to-br from-rose-50 to-pink-100/50 border-rose-200/60 dark:from-rose-900/30 dark:to-pink-900/20 dark:border-rose-700/30" data-testid="expenses-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-rose-700 dark:text-rose-300">Expenses</CardTitle>
              <div className="w-8 h-8 rounded-lg bg-rose-500/20 flex items-center justify-center">
                <TrendingDown className="w-4 h-4 text-rose-600 dark:text-rose-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-rose-700 dark:text-rose-300 tabular-nums">
                {formatCurrency(summary.expenses)}
              </div>
              <div className="flex items-center justify-end mt-1">
                {summary.expenses_change !== 0 && (
                  <span className={`text-xs flex items-center gap-0.5 ${
                    summary.expenses_change < 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'
                  }`}>
                    {summary.expenses_change < 0 ? <ArrowDownRight className="w-3 h-3" /> : <ArrowUpRight className="w-3 h-3" />}
                    {Math.abs(formatChange(summary.expenses, summary.prev_expenses) || 0)}% vs last month
                  </span>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover bg-gradient-to-br from-violet-50 to-purple-100/50 border-violet-200/60 dark:from-violet-900/30 dark:to-purple-900/20 dark:border-violet-700/30" data-testid="budget-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-violet-700 dark:text-violet-300">To Budget</CardTitle>
              <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
                <Target className="w-4 h-4 text-violet-600 dark:text-violet-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold tabular-nums ${
                summary.to_budget >= 0 ? 'text-violet-700 dark:text-violet-300' : 'text-rose-600 dark:text-rose-400'
              }`}>
                {formatCurrency(summary.to_budget)}
              </div>
              <p className="text-xs text-violet-600/70 dark:text-violet-400/70 mt-1">
                {summary.to_budget >= 0 ? "Remaining this month" : "Over budget"}
              </p>
            </CardContent>
          </Card>

          <Card className="card-hover bg-gradient-to-br from-blue-50 to-indigo-100/50 border-blue-200/60 dark:from-blue-900/30 dark:to-indigo-900/20 dark:border-blue-700/30" data-testid="net-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-blue-700 dark:text-blue-300">Net Position</CardTitle>
              <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Wallet className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold tabular-nums ${
                summary.net >= 0 ? 'text-blue-700 dark:text-blue-300' : 'text-rose-600 dark:text-rose-400'
              }`}>
                {formatCurrency(summary.net)}
              </div>
              <p className="text-xs text-blue-600/70 dark:text-blue-400/70 mt-1">Income - Expenses</p>
            </CardContent>
          </Card>
        </div>

        {/* Spending Chart */}
        <Card data-testid="spending-chart-card">
          <CardHeader>
            <CardTitle className="text-lg">Spending This Month vs Last Month</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height={300}>
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
                    stroke="#3B82F6" 
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

        {/* Monthly Spending by Category */}
        <Card data-testid="category-spending-card" className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between bg-gradient-to-r from-violet-500/5 to-purple-500/5 border-b border-border/50">
            <CardTitle className="text-lg flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                <Target className="w-4 h-4 text-white" />
              </div>
              Monthly Spending by Category
            </CardTitle>
            <div className="px-3 py-1.5 rounded-full bg-gradient-to-r from-violet-500/10 to-purple-500/10 border border-violet-500/20">
              <span className="text-sm font-semibold text-violet-600 dark:text-violet-400">
                {formatCurrency(categorySpending.total)}
              </span>
            </div>
          </CardHeader>
          <CardContent className="pt-5">
            {categorySpending.categories.length === 0 ? (
              <div className="text-center text-muted-foreground py-6">
                No spending this month
              </div>
            ) : (
              <div className="space-y-4">
                {categorySpending.categories.slice(0, 8).map((cat, idx) => {
                  // Vibrant fallback colors if category doesn't have one
                  const fallbackColors = [
                    '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', 
                    '#3B82F6', '#EF4444', '#06B6D4', '#F97316'
                  ];
                  const categoryColor = cat.color || fallbackColors[idx % fallbackColors.length];
                  
                  return (
                    <div key={cat.name} className="group">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <div 
                            className="w-4 h-4 rounded-md shadow-sm" 
                            style={{ 
                              backgroundColor: categoryColor,
                              boxShadow: `0 2px 8px ${categoryColor}40`
                            }}
                          />
                          <span className="text-sm font-medium">{cat.name}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="flex items-center gap-1.5">
                            <div 
                              className="w-2 h-2 rounded-full animate-pulse"
                              style={{ backgroundColor: categoryColor }}
                            />
                            <span className="text-xs font-medium px-2 py-0.5 rounded-full" 
                              style={{ 
                                backgroundColor: `${categoryColor}15`,
                                color: categoryColor 
                              }}>
                              {cat.percentage}%
                            </span>
                          </div>
                          <span className="text-sm font-bold tabular-nums min-w-[80px] text-right">
                            {formatCurrency(cat.amount)}
                          </span>
                        </div>
                      </div>
                      <div className="h-3 bg-secondary/60 rounded-full overflow-hidden shadow-inner">
                        <div 
                          className="h-full rounded-full transition-all duration-700 ease-out relative"
                          style={{ 
                            width: `${cat.percentage}%`,
                            background: `linear-gradient(90deg, ${categoryColor}, ${categoryColor}CC)`,
                            boxShadow: `0 0 10px ${categoryColor}60`
                          }}
                        >
                          <div className="absolute inset-0 bg-gradient-to-b from-white/20 to-transparent rounded-full" />
                        </div>
                      </div>
                    </div>
                  );
                })}
                {categorySpending.categories.length > 8 && (
                  <Link 
                    to="/reports" 
                    className="text-sm text-violet-500 hover:text-violet-600 font-medium flex items-center gap-1 pt-2 transition-colors"
                  >
                    View all categories <ArrowRight className="w-3 h-3" />
                  </Link>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Main Grid - Transactions & Recurring */}
        <div className="dashboard-grid">
          {/* Recent Transactions */}
          <Card data-testid="recent-transactions-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Recent Transactions</CardTitle>
              <Link to="/transactions" className="text-sm text-blue-500 hover:underline flex items-center gap-1">
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
                      <div key={tx.id} className="px-4 py-3 flex items-center justify-between hover:bg-secondary/30 transition-colors">
                        <div className="flex items-center gap-3 min-w-0">
                          <div 
                            className="w-2 h-8 rounded-full" 
                            style={{ backgroundColor: category?.color || "#64748B" }}
                          />
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
                        <div className={`font-medium tabular-nums ${
                          tx.amount >= 0 ? 'text-emerald-600 dark:text-emerald-400' : ''
                        }`}>
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
              <Link to="/recurring" className="text-sm text-blue-500 hover:underline flex items-center gap-1">
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
                    <div key={item.id} className="px-4 py-3 flex items-center justify-between hover:bg-secondary/30 transition-colors">
                      <div className="flex items-center gap-3">
                        <RefreshCw className="w-4 h-4 text-muted-foreground" />
                        <div>
                          <span className="font-medium">{item.name}</span>
                          <p className="text-xs text-muted-foreground">
                            Due {formatShortDate(item.next_date)}
                          </p>
                        </div>
                      </div>
                      <span className={`font-medium tabular-nums ${
                        item.type === 'income' ? 'text-emerald-600 dark:text-emerald-400' : ''
                      }`}>
                        {formatCurrency(Math.abs(item.amount))}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Goals */}
        <Card data-testid="goals-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Goals</CardTitle>
            <Link to="/goals" className="text-sm text-blue-500 hover:underline flex items-center gap-1">
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
                      className="p-4 rounded-xl border border-border bg-secondary/20"
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
                      <div className="h-2 bg-secondary rounded-full overflow-hidden">
                        <div 
                          className="h-full rounded-full transition-all duration-500"
                          style={{ 
                            width: `${Math.min(progress, 100)}%`,
                            backgroundColor: goal.color
                          }}
                        />
                      </div>
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
