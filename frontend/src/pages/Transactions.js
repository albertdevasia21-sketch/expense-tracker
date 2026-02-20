import React, { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Plus, Search, Filter, Trash2, ChevronDown, X } from "lucide-react";
import { Card, CardContent } from "../components/ui/card";
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
import { formatCurrency, formatDate, getCurrentMonth, getMemberColor } from "../lib/utils";
import { toast } from "sonner";

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

  const handleDelete = async (e, txId) => {
    e.stopPropagation();
    if (!window.confirm("Delete this transaction?")) return;
    
    try {
      await api.delete(`/transactions/${txId}`);
      toast.success("Transaction deleted");
      fetchTransactions();
    } catch (error) {
      console.error("Failed to delete:", error);
      toast.error("Failed to delete transaction");
    }
  };

  const openNew = () => {
    setSelectedTransaction(null);
    setDrawerOpen(true);
  };

  const openEdit = (tx) => {
    setSelectedTransaction(tx);
    setDrawerOpen(true);
  };

  // Filter and sort
  const filteredTransactions = transactions.filter((tx) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      tx.merchant_name?.toLowerCase().includes(searchLower) ||
      tx.notes?.toLowerCase().includes(searchLower)
    );
  }).sort((a, b) => new Date(b.date) - new Date(a.date));

  // Calculate totals
  const totalIncome = transactions.filter(t => t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
  const totalExpenses = transactions.filter(t => t.amount < 0).reduce((sum, t) => sum + Math.abs(t.amount), 0);

  // Get first letter for transaction icon
  const getInitial = (name) => {
    return (name || "T").charAt(0).toUpperCase();
  };

  // Get color for category badge
  const getCategoryColor = (category) => {
    if (!category) return { bg: "bg-gray-100 dark:bg-gray-800", text: "text-gray-600 dark:text-gray-400" };
    const colors = {
      "Housing": { bg: "bg-violet-100 dark:bg-violet-900/30", text: "text-violet-700 dark:text-violet-400" },
      "Transportation": { bg: "bg-amber-100 dark:bg-amber-900/30", text: "text-amber-700 dark:text-amber-400" },
      "Food": { bg: "bg-emerald-100 dark:bg-emerald-900/30", text: "text-emerald-700 dark:text-emerald-400" },
      "Utilities": { bg: "bg-cyan-100 dark:bg-cyan-900/30", text: "text-cyan-700 dark:text-cyan-400" },
      "Insurance": { bg: "bg-pink-100 dark:bg-pink-900/30", text: "text-pink-700 dark:text-pink-400" },
      "Shopping": { bg: "bg-orange-100 dark:bg-orange-900/30", text: "text-orange-700 dark:text-orange-400" },
      "Health": { bg: "bg-red-100 dark:bg-red-900/30", text: "text-red-700 dark:text-red-400" },
      "Entertainment": { bg: "bg-purple-100 dark:bg-purple-900/30", text: "text-purple-700 dark:text-purple-400" },
      "Income": { bg: "bg-green-100 dark:bg-green-900/30", text: "text-green-700 dark:text-green-400" },
    };
    return colors[category.group_name] || { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-400" };
  };

  return (
    <div data-testid="transactions-page">
      <PageHeader
        title="Transactions"
        subtitle="Manage your income and expenses"
        month={month}
        setMonth={setMonth}
        onMenuClick={onMenuClick}
        actions={
          <Button onClick={openNew} className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700" data-testid="add-transaction-btn">
            <Plus className="w-4 h-4 mr-2" />
            Add Transaction
          </Button>
        }
      />

      <div className="page-content space-y-4">
        {/* Search and Filters Bar */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search transactions..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-10"
              data-testid="search-input"
            />
          </div>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="h-10"
            data-testid="filter-toggle-btn"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
            <ChevronDown className={`w-4 h-4 ml-2 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </Button>
        </div>

        {/* Filters */}
        {showFilters && (
          <Card className="border-dashed">
            <CardContent className="p-4">
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Person</label>
                  <Select value={memberFilter} onValueChange={setMemberFilter}>
                    <SelectTrigger data-testid="member-filter">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Members</SelectItem>
                      {members.map((m) => (
                        <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Category</label>
                  <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                    <SelectTrigger data-testid="category-filter">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Categories</SelectItem>
                      {categories.map((c) => (
                        <SelectItem key={c.id} value={c.id}>{c.category_name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Account</label>
                  <Select value={accountFilter} onValueChange={setAccountFilter}>
                    <SelectTrigger data-testid="account-filter">
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

        {/* Summary Pills */}
        <div className="flex gap-3">
          <div className="px-4 py-2 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800">
            <span className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
              Income: {formatCurrency(totalIncome)}
            </span>
          </div>
          <div className="px-4 py-2 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800">
            <span className="text-sm text-rose-600 dark:text-rose-400 font-medium">
              Expenses: {formatCurrency(totalExpenses)}
            </span>
          </div>
        </div>

        {/* Transactions Table */}
        <Card className="overflow-hidden" data-testid="transactions-list">
          <div className="overflow-x-auto">
            {/* Table Header */}
            <div className="grid grid-cols-[auto,1fr,auto,auto,auto,auto,auto] gap-4 px-4 py-3 bg-secondary/50 border-b text-sm font-medium text-muted-foreground min-w-[800px]">
              <div className="w-10"></div>
              <div>Transaction</div>
              <div className="w-28">Category</div>
              <div className="w-20">Person</div>
              <div className="w-24">Date</div>
              <div className="w-24 text-right">Amount</div>
              <div className="w-10"></div>
            </div>

            {/* Table Body */}
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="loading-spinner" />
              </div>
            ) : filteredTransactions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mb-4">
                  <Search className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-medium">No transactions found</h3>
                <p className="text-muted-foreground mt-1">
                  {search ? "Try a different search term" : "Add your first transaction to get started"}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border min-w-[800px]">
                {filteredTransactions.map((tx) => {
                  const member = getMemberById(tx.member_id);
                  const category = getCategoryById(tx.category_id);
                  const account = getAccountById(tx.account_id);
                  const categoryColors = getCategoryColor(category);
                  const memberColors = getMemberColor(member?.name);
                  
                  return (
                    <div 
                      key={tx.id}
                      className="grid grid-cols-[auto,1fr,auto,auto,auto,auto,auto] gap-4 px-4 py-3 items-center hover:bg-secondary/30 cursor-pointer transition-colors group"
                      onClick={() => openEdit(tx)}
                      data-testid={`transaction-${tx.id}`}
                    >
                      {/* Icon */}
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-semibold ${
                        tx.amount >= 0 
                          ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                      }`}>
                        {getInitial(tx.merchant_name)}
                      </div>
                      
                      {/* Transaction Name */}
                      <div className="min-w-0">
                        <div className="font-medium truncate">{tx.merchant_name || "Transaction"}</div>
                        {account && (
                          <div className="text-xs text-muted-foreground truncate">{account.name}</div>
                        )}
                      </div>
                      
                      {/* Category */}
                      <div className="w-28">
                        <span className={`inline-flex px-2.5 py-1 rounded-lg text-xs font-medium ${categoryColors.bg} ${categoryColors.text}`}>
                          {category?.category_name || "Uncategorized"}
                        </span>
                      </div>
                      
                      {/* Person */}
                      <div className="w-20">
                        {member && (
                          <span className={`inline-flex px-2.5 py-1 rounded-lg text-xs font-medium ${memberColors.bg} ${memberColors.text}`}>
                            {member.name}
                          </span>
                        )}
                      </div>
                      
                      {/* Date */}
                      <div className="w-24 text-sm text-muted-foreground">
                        {formatDate(tx.date)}
                      </div>
                      
                      {/* Amount */}
                      <div className={`w-24 text-right font-semibold tabular-nums ${
                        tx.amount >= 0 
                          ? 'text-emerald-600 dark:text-emerald-400' 
                          : 'text-slate-900 dark:text-slate-100'
                      }`}>
                        {tx.amount >= 0 ? '+' : ''}{formatCurrency(tx.amount)}
                      </div>
                      
                      {/* Delete */}
                      <div className="w-10">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20"
                          onClick={(e) => handleDelete(e, tx.id)}
                          data-testid={`delete-tx-${tx.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
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
