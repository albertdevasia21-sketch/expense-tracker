import React, { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Download, DollarSign, Receipt, TrendingDown, Target } from "lucide-react";
import { 
  PieChart, 
  Pie, 
  Cell, 
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  CartesianGrid
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { PageHeader } from "../components/layout/PageHeader";
import { useAuth } from "../contexts/AuthContext";
import { useData } from "../contexts/DataContext";
import { formatCurrency, getCurrentMonth } from "../lib/utils";
import { toast } from "sonner";

export default function Reports() {
  const { onMenuClick } = useOutletContext();
  const { api } = useAuth();
  const { members, categories, subcategories, accounts, getSubcategoriesForCategory } = useData();
  
  const currentMonth = getCurrentMonth();
  const [startDate, setStartDate] = useState(`${currentMonth}-01`);
  const [endDate, setEndDate] = useState(`${currentMonth}-31`);
  const [memberFilter, setMemberFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [subcategoryFilter, setSubcategoryFilter] = useState("all");
  const [accountFilter, setAccountFilter] = useState("all");
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Get available subcategories for selected category
  const availableSubcategories = categoryFilter !== "all" 
    ? getSubcategoriesForCategory(categoryFilter)
    : [];

  useEffect(() => {
    fetchReportData();
  }, [startDate, endDate, memberFilter, categoryFilter, subcategoryFilter, accountFilter]);

  // Reset subcategory when category changes
  useEffect(() => {
    setSubcategoryFilter("all");
  }, [categoryFilter]);

  const fetchReportData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);
      if (memberFilter !== "all") params.append("member_id", memberFilter);
      if (categoryFilter !== "all") params.append("category_id", categoryFilter);
      if (subcategoryFilter !== "all") params.append("subcategory_id", subcategoryFilter);
      if (accountFilter !== "all") params.append("account_id", accountFilter);

      const [summaryRes, txRes] = await Promise.all([
        api.get(`/reports/summary?${params.toString()}`),
        api.get(`/transactions?${params.toString()}`),
      ]);

      setSummary(summaryRes.data);
      setTransactions(txRes.data);
    } catch (error) {
      console.error("Failed to fetch report data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);
      if (memberFilter !== "all") params.append("member_id", memberFilter);

      const response = await api.get(`/export/transactions?${params.toString()}`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `transactions-${startDate}-to-${endDate}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success("Export downloaded");
    } catch (error) {
      console.error("Export failed:", error);
      toast.error("Failed to export");
    }
  };

  // Spending over time
  const spendingByDate = transactions
    .filter(t => t.amount < 0)
    .reduce((acc, t) => {
      const day = t.date.split("-")[2];
      acc[day] = (acc[day] || 0) + Math.abs(t.amount);
      return acc;
    }, {});

  const spendingOverTime = Object.entries(spendingByDate)
    .map(([day, amount]) => ({ day: parseInt(day), amount }))
    .sort((a, b) => a.day - b.day);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-card border border-border rounded-lg shadow-lg p-3">
          <p className="text-sm font-medium">{payload[0].name || `Day ${label}`}</p>
          <p className="text-sm" style={{ color: payload[0].payload?.color || '#3B82F6' }}>
            {formatCurrency(payload[0].value)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div data-testid="reports-page">
      <PageHeader
        title="Reports"
        subtitle="Analyze your spending patterns"
        showMonthSelector={false}
        onMenuClick={onMenuClick}
        actions={
          <Button onClick={handleExport} variant="outline" data-testid="export-btn">
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        }
      />

      <div className="page-content space-y-6">
        {/* Filters */}
        <Card data-testid="filters-card">
          <CardContent className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div>
                <Label className="mb-1.5 block text-xs text-muted-foreground">Start Date</Label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="h-9"
                  data-testid="start-date-input"
                />
              </div>
              <div>
                <Label className="mb-1.5 block text-xs text-muted-foreground">End Date</Label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="h-9"
                  data-testid="end-date-input"
                />
              </div>
              <div>
                <Label className="mb-1.5 block text-xs text-muted-foreground">Member</Label>
                <Select value={memberFilter} onValueChange={setMemberFilter}>
                  <SelectTrigger className="h-9" data-testid="report-member-filter">
                    <SelectValue placeholder="All" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Members</SelectItem>
                    {members.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: m.color }} />
                          {m.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="mb-1.5 block text-xs text-muted-foreground">Category</Label>
                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                  <SelectTrigger className="h-9" data-testid="report-category-filter">
                    <SelectValue placeholder="All" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    {categories.filter(c => c.type === "expense").map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: c.color }} />
                          {c.category_name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="mb-1.5 block text-xs text-muted-foreground">Subcategory</Label>
                <Select 
                  value={subcategoryFilter} 
                  onValueChange={setSubcategoryFilter}
                  disabled={categoryFilter === "all"}
                >
                  <SelectTrigger className="h-9" data-testid="report-subcategory-filter">
                    <SelectValue placeholder="All" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Subcategories</SelectItem>
                    {availableSubcategories.map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="mb-1.5 block text-xs text-muted-foreground">Account</Label>
                <Select value={accountFilter} onValueChange={setAccountFilter}>
                  <SelectTrigger className="h-9" data-testid="report-account-filter">
                    <SelectValue placeholder="All" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Accounts</SelectItem>
                    {accounts.map((a) => (
                      <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* KPI Cards */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20" data-testid="total-spent-card">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Spent</CardTitle>
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                  <DollarSign className="w-4 h-4 text-blue-500" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">{formatCurrency(summary.total_spent)}</div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20" data-testid="transactions-count-card">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Transactions</CardTitle>
                <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                  <Receipt className="w-4 h-4 text-purple-500" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">{summary.transaction_count}</div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20" data-testid="avg-transaction-card">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Avg Transaction</CardTitle>
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center">
                  <TrendingDown className="w-4 h-4 text-amber-500" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">{formatCurrency(summary.avg_transaction)}</div>
              </CardContent>
            </Card>

            <Card className={`bg-gradient-to-br ${summary.budget_usage > 100 ? 'from-red-500/10 to-red-600/5 border-red-500/20' : 'from-emerald-500/10 to-emerald-600/5 border-emerald-500/20'}`} data-testid="budget-usage-card">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Budget Usage</CardTitle>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${summary.budget_usage > 100 ? 'bg-red-500/20' : 'bg-emerald-500/20'}`}>
                  <Target className={`w-4 h-4 ${summary.budget_usage > 100 ? 'text-red-500' : 'text-emerald-500'}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold tabular-nums ${summary.budget_usage > 100 ? 'text-red-600 dark:text-red-400' : ''}`}>
                  {summary.budget_usage}%
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Category Summary Table + Pie Chart */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Category Summary Table */}
          <Card data-testid="category-table-card">
            <CardHeader>
              <CardTitle>Spending by Category</CardTitle>
            </CardHeader>
            <CardContent>
              {summary?.by_category?.length > 0 ? (
                <div className="space-y-3">
                  {summary.by_category.slice(0, 10).map((item) => (
                    <div key={item.name} className="flex items-center gap-3">
                      <div 
                        className="w-3 h-3 rounded-full shrink-0" 
                        style={{ backgroundColor: item.color }}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium truncate">{item.name}</span>
                          <span className="text-sm font-semibold tabular-nums">{formatCurrency(item.value)}</span>
                        </div>
                        <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                          <div 
                            className="h-full rounded-full"
                            style={{ 
                              width: `${item.percentage}%`,
                              backgroundColor: item.color
                            }}
                          />
                        </div>
                      </div>
                      <span className="text-xs text-muted-foreground w-12 text-right shrink-0">
                        {item.percentage}%
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pie Chart */}
          <Card data-testid="category-pie-chart">
            <CardHeader>
              <CardTitle>Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              {summary?.by_category?.length > 0 ? (
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={summary.by_category.slice(0, 8)}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {summary.by_category.slice(0, 8).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Spending Over Time + By Member */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Spending Over Time */}
          <Card data-testid="spending-line-chart">
            <CardHeader>
              <CardTitle>Spending Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              {spendingOverTime.length > 0 ? (
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={spendingOverTime}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="day" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickFormatter={(v) => `$${v}`} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="amount" stroke="#3B82F6" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* By Member */}
          <Card data-testid="member-bar-chart">
            <CardHeader>
              <CardTitle>Spending by Household Member</CardTitle>
            </CardHeader>
            <CardContent>
              {summary?.by_member?.length > 0 ? (
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={summary.by_member} layout="vertical">
                      <XAxis type="number" tickFormatter={(v) => `$${v}`} />
                      <YAxis type="category" dataKey="name" width={80} />
                      <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(var(--secondary))' }} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {summary.by_member.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color || '#3B82F6'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
