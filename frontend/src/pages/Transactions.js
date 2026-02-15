import React, { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Plus, Search, Filter, Edit2, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "../components/ui/select";
import { PageHeader } from "../components/layout/PageHeader";
import { TransactionDrawer } from "../components/transactions/TransactionDrawer";
import { useAuth } from "../contexts/AuthContext";
import { useData } from "../contexts/DataContext";
import { formatCurrency, formatDate, getCurrentMonth, getMemberColor, groupBy } from "../lib/utils";

export default function Transactions() {
  const { onMenuClick } = useOutletContext();
  const { api } = useAuth();
  const { members, getCategoryById, getMemberById, getAccountById, categories, accounts } = useData();
  
  const [month, setMonth] = useState(getCurrentMonth());
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [search, setSearch] = useState("");
  const [memberFilter, setMemberFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [accountFilter, setAccountFilter] = useState("all");
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchTransactions();
  }, [month, memberFilter, categoryFilter, accountFilter]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ month });
      if (memberFilter !== "all") params.append("member_id", memberFilter);
      if (categoryFilter !== "all") params.append("category_id", categoryFilter);
      if (accountFilter !== "all") params.append("account_id", accountFilter);
      
      const response = await api.get(`/transactions?${params.toString()}`);
      setTransactions(response.data);
    } catch (error) {
      console.error("Failed to fetch transactions:", error);
    } finally {
      setLoading(false);
    }
  };

  const openEdit = (transaction) => {
    setSelectedTransaction(transaction);
    setDrawerOpen(true);
  };

  const openNew = () => {
    setSelectedTransaction(null);
    setDrawerOpen(true);
  };

  const filteredTransactions = transactions.filter((tx) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      tx.merchant_name?.toLowerCase().includes(searchLower) ||
      tx.notes?.toLowerCase().includes(searchLower)
    );
  });

  const groupedTransactions = groupBy(filteredTransactions, "date");
  const sortedDates = Object.keys(groupedTransactions).sort((a, b) => b.localeCompare(a));

  const totalIncome = filteredTransactions.filter(t => t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
  const totalExpenses = filteredTransactions.filter(t => t.amount < 0).reduce((sum, t) => sum + Math.abs(t.amount), 0);

  return (
    <div data-testid="transactions-page">
      <PageHeader
        title="Transactions"
        subtitle={`${filteredTransactions.length} transactions`}
        month={month}
        setMonth={setMonth}
        onMenuClick={onMenuClick}
        actions={
          <Button onClick={openNew} data-testid="add-transaction-btn">
            <Plus className="w-4 h-4 mr-2" />
            Add Transaction
          </Button>
        }
      />

      <div className="page-content space-y-4">
        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search transactions..."
              className="pl-10"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              data-testid="search-input"
            />
          </div>
          <Button 
            variant="outline" 
            onClick={() => setShowFilters(!showFilters)}
            data-testid="filter-btn"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
            {(memberFilter !== "all" || categoryFilter !== "all" || accountFilter !== "all") && (
              <span className="ml-2 w-5 h-5 rounded-full bg-accent text-accent-foreground text-xs flex items-center justify-center">
                !
              </span>
            )}
          </Button>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <Card className="animate-fade-in" data-testid="filter-panel">
            <CardContent className="p-4">
              <div className="flex flex-wrap gap-4">
                <div className="flex-1 min-w-[150px]">
                  <label className="text-sm font-medium mb-1.5 block">Member</label>
                  <Select value={memberFilter} onValueChange={setMemberFilter}>
                    <SelectTrigger data-testid="member-filter">
                      <SelectValue placeholder="All members" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All members</SelectItem>
                      {members.map((m) => (
                        <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1 min-w-[150px]">
                  <label className="text-sm font-medium mb-1.5 block">Category</label>
                  <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                    <SelectTrigger data-testid="category-filter">
                      <SelectValue placeholder="All categories" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All categories</SelectItem>
                      {categories.map((c) => (
                        <SelectItem key={c.id} value={c.id}>{c.category_name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1 min-w-[150px]">
                  <label className="text-sm font-medium mb-1.5 block">Account</label>
                  <Select value={accountFilter} onValueChange={setAccountFilter}>
                    <SelectTrigger data-testid="account-filter">
                      <SelectValue placeholder="All accounts" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All accounts</SelectItem>
                      {accounts.map((a) => (
                        <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-end">
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => {
                      setMemberFilter("all");
                      setCategoryFilter("all");
                      setAccountFilter("all");
                    }}
                    data-testid="clear-filters-btn"
                  >
                    <X className="w-4 h-4 mr-1" />
                    Clear
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Summary */}
        <div className="flex gap-4 text-sm">
          <div className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-100 to-teal-100 dark:from-emerald-900/40 dark:to-teal-900/30 text-emerald-700 dark:text-emerald-400 font-medium shadow-sm border border-emerald-200/50 dark:border-emerald-700/30">
            <span className="text-emerald-500 mr-1">↑</span> Income: {formatCurrency(totalIncome)}
          </div>
          <div className="px-4 py-2 rounded-xl bg-gradient-to-r from-rose-100 to-pink-100 dark:from-rose-900/40 dark:to-pink-900/30 text-rose-700 dark:text-rose-400 font-medium shadow-sm border border-rose-200/50 dark:border-rose-700/30">
            <span className="text-rose-500 mr-1">↓</span> Expenses: {formatCurrency(totalExpenses)}
          </div>
        </div>

        {/* Transactions List */}
        <Card data-testid="transactions-list" className="overflow-hidden shadow-sm">
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="loading-spinner" />
              </div>
            ) : filteredTransactions.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">
                  <Search className="w-full h-full" />
                </div>
                <h3 className="text-lg font-medium">No transactions found</h3>
                <p className="text-muted-foreground mt-1">
                  {search ? "Try a different search term" : "Add your first transaction to get started"}
                </p>
              </div>
            ) : (
              <div>
                {sortedDates.map((date) => (
                  <div key={date}>
                    <div className="px-4 py-2.5 bg-gradient-to-r from-secondary/80 to-secondary/40 text-sm font-semibold sticky top-0 border-b border-border/50 backdrop-blur-sm">
                      {formatDate(date)}
                    </div>
                    {groupedTransactions[date].map((tx) => {
                      const member = getMemberById(tx.member_id);
                      const category = getCategoryById(tx.category_id);
                      const account = getAccountById(tx.account_id);
                      const memberColors = getMemberColor(member?.name);
                      
                      return (
                        <div 
                          key={tx.id} 
                          className="transaction-item cursor-pointer"
                          onClick={() => openEdit(tx)}
                          data-testid={`transaction-${tx.id}`}
                        >
                          <div className="flex items-center gap-4 min-w-0 flex-1">
                            <div className="flex flex-col min-w-0">
                              <span className="font-medium truncate">
                                {tx.merchant_name || "Transaction"}
                              </span>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                                <span>{category?.category_name || "Uncategorized"}</span>
                                {account && (
                                  <span className="px-1.5 py-0.5 rounded bg-secondary">
                                    {account.name}
                                  </span>
                                )}
                                {member && (
                                  <span className={`px-1.5 py-0.5 rounded ${memberColors.bg} ${memberColors.text}`}>
                                    {member.name}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className={`font-medium tabular-nums ${tx.amount >= 0 ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>
                              {formatCurrency(tx.amount)}
                            </span>
                            <Edit2 className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <TransactionDrawer
        isOpen={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedTransaction(null);
        }}
        transaction={selectedTransaction}
        onSave={fetchTransactions}
      />
    </div>
  );
}
