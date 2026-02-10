import React, { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { TrendingUp, TrendingDown, ArrowRightLeft } from "lucide-react";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "../components/ui/tabs";
import { PageHeader } from "../components/layout/PageHeader";
import { useAuth } from "../contexts/AuthContext";
import { useData } from "../contexts/DataContext";
import { formatCurrency, getCurrentMonth } from "../lib/utils";

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6', '#06B6D4', '#F97316', '#6366F1'];

export default function CashFlow() {
  const { onMenuClick } = useOutletContext();
  const { api } = useAuth();
  const { members, getCategoryById } = useData();
  
  const [month, setMonth] = useState(getCurrentMonth());
  const [memberFilter, setMemberFilter] = useState("all");
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTransactions();
  }, [month, memberFilter]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ month });
      if (memberFilter !== "all") params.append("member_id", memberFilter);
      
      const response = await api.get(`/transactions?${params.toString()}`);
      setTransactions(response.data);
    } catch (error) {
      console.error("Failed to fetch transactions:", error);
    } finally {
      setLoading(false);
    }
  };

  const income = transactions.filter(t => t.amount > 0);
  const expenses = transactions.filter(t => t.amount < 0);
  
  const totalIncome = income.reduce((sum, t) => sum + t.amount, 0);
  const totalExpenses = expenses.reduce((sum, t) => sum + Math.abs(t.amount), 0);
  const netCashFlow = totalIncome - totalExpenses;

  // Income by category
  const incomeByCategory = income.reduce((acc, t) => {
    const cat = getCategoryById(t.category_id);
    const name = cat?.category_name || "Other";
    acc[name] = (acc[name] || 0) + t.amount;
    return acc;
  }, {});

  const incomeData = Object.entries(incomeByCategory)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  // Expenses by category
  const expensesByCategory = expenses.reduce((acc, t) => {
    const cat = getCategoryById(t.category_id);
    const name = cat?.category_name || "Other";
    acc[name] = (acc[name] || 0) + Math.abs(t.amount);
    return acc;
  }, {});

  const expenseData = Object.entries(expensesByCategory)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="text-sm font-medium">{payload[0].name}</p>
          <p className="text-sm text-accent">{formatCurrency(payload[0].value)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div data-testid="cashflow-page">
      <PageHeader
        title="Cash Flow"
        subtitle="Track money in and out"
        month={month}
        setMonth={setMonth}
        onMenuClick={onMenuClick}
      />

      <div className="page-content space-y-6">
        {/* Member Filter */}
        <Tabs value={memberFilter} onValueChange={setMemberFilter}>
          <TabsList data-testid="member-tabs">
            <TabsTrigger value="all">All</TabsTrigger>
            {members.map((m) => (
              <TabsTrigger key={m.id} value={m.id}>{m.name}</TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card data-testid="income-total-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Income</CardTitle>
              <TrendingUp className="w-4 h-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                {formatCurrency(totalIncome)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">{income.length} transactions</p>
            </CardContent>
          </Card>

          <Card data-testid="expenses-total-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Expenses</CardTitle>
              <TrendingDown className="w-4 h-4 text-rose-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-rose-600 dark:text-rose-400 tabular-nums">
                {formatCurrency(totalExpenses)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">{expenses.length} transactions</p>
            </CardContent>
          </Card>

          <Card data-testid="net-cashflow-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Net Cash Flow</CardTitle>
              <ArrowRightLeft className="w-4 h-4 text-accent" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold tabular-nums ${netCashFlow >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                {formatCurrency(netCashFlow)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {netCashFlow >= 0 ? "Positive cash flow" : "Negative cash flow"}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Income Chart */}
          <Card data-testid="income-chart-card">
            <CardHeader>
              <CardTitle>Income by Source</CardTitle>
            </CardHeader>
            <CardContent>
              {incomeData.length === 0 ? (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                  No income this month
                </div>
              ) : (
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={incomeData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {incomeData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
              <div className="mt-4 space-y-2">
                {incomeData.slice(0, 5).map((item, idx) => (
                  <div key={item.name} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                      />
                      <span className="truncate">{item.name}</span>
                    </div>
                    <span className="font-medium tabular-nums">{formatCurrency(item.value)}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Expenses Chart */}
          <Card data-testid="expenses-chart-card">
            <CardHeader>
              <CardTitle>Expenses by Category</CardTitle>
            </CardHeader>
            <CardContent>
              {expenseData.length === 0 ? (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                  No expenses this month
                </div>
              ) : (
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={expenseData.slice(0, 8)} layout="vertical">
                      <XAxis type="number" tickFormatter={(v) => `$${v}`} />
                      <YAxis 
                        type="category" 
                        dataKey="name" 
                        width={100}
                        tick={{ fontSize: 12 }}
                      />
                      <Tooltip 
                        content={<CustomTooltip />}
                        cursor={{ fill: 'hsl(var(--secondary))' }}
                      />
                      <Bar dataKey="value" fill="hsl(var(--accent))" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
