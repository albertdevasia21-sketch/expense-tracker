import React, { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Plus, TrendingUp, TrendingDown, Target, Pencil, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Progress } from "../components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { Switch } from "../components/ui/switch";
import { PageHeader } from "../components/layout/PageHeader";
import { useAuth } from "../contexts/AuthContext";
import { useData } from "../contexts/DataContext";
import { formatCurrency, getCurrentMonth, groupBy } from "../lib/utils";
import { toast } from "sonner";

export default function Budget() {
  const { onMenuClick } = useOutletContext();
  const { api } = useAuth();
  const { categories, getCategoryById, expenseCategories, fixedCategories, flexibleCategories } = useData();
  
  const [month, setMonth] = useState(getCurrentMonth());
  const [budgets, setBudgets] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState(null);
  const [formData, setFormData] = useState({
    category_id: "",
    amount: "",
    rollover: false,
  });

  useEffect(() => {
    fetchBudgetData();
  }, [month]);

  const fetchBudgetData = async () => {
    setLoading(true);
    try {
      const [budgetRes, txRes] = await Promise.all([
        api.get(`/budgets?month=${month}`),
        api.get(`/transactions?month=${month}`),
      ]);
      setBudgets(budgetRes.data);
      setTransactions(txRes.data);
    } catch (error) {
      console.error("Failed to fetch budget data:", error);
    } finally {
      setLoading(false);
    }
  };

  // Calculate totals
  const income = transactions.filter(t => t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
  const expenses = transactions.filter(t => t.amount < 0).reduce((sum, t) => sum + Math.abs(t.amount), 0);
  const totalBudget = budgets.reduce((sum, b) => sum + b.amount, 0);
  const leftToBudget = totalBudget - expenses;

  // Group budgets with actual spending
  const budgetData = budgets.map(budget => {
    const cat = getCategoryById(budget.category_id);
    const spent = transactions
      .filter(t => t.category_id === budget.category_id && t.amount < 0)
      .reduce((sum, t) => sum + Math.abs(t.amount), 0);
    
    return {
      ...budget,
      category: cat,
      spent,
      remaining: budget.amount - spent,
      percentage: budget.amount > 0 ? (spent / budget.amount) * 100 : 0,
    };
  });

  // Group by fixed/flexible
  const fixedBudgets = budgetData.filter(b => b.category?.is_fixed);
  const flexibleBudgets = budgetData.filter(b => !b.category?.is_fixed);

  const openNew = () => {
    setEditingBudget(null);
    setFormData({ category_id: "", amount: "", rollover: false });
    setDialogOpen(true);
  };

  const openEdit = (budget) => {
    setEditingBudget(budget);
    setFormData({
      category_id: budget.category_id,
      amount: budget.amount.toString(),
      rollover: budget.rollover,
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        month,
        category_id: formData.category_id,
        amount: parseFloat(formData.amount),
        rollover: formData.rollover,
      };

      if (editingBudget) {
        await api.put(`/budgets/${editingBudget.id}`, payload);
        toast.success("Budget updated");
      } else {
        await api.post("/budgets", payload);
        toast.success("Budget created");
      }
      
      await fetchBudgetData();
      setDialogOpen(false);
    } catch (error) {
      console.error("Failed to save budget:", error);
      toast.error("Failed to save budget");
    }
  };

  const handleDelete = async (budgetId) => {
    if (!window.confirm("Delete this budget?")) return;
    
    try {
      await api.delete(`/budgets/${budgetId}`);
      toast.success("Budget deleted");
      await fetchBudgetData();
    } catch (error) {
      console.error("Failed to delete budget:", error);
      toast.error("Failed to delete budget");
    }
  };

  const BudgetSection = ({ title, items, isFixed }) => (
    <Card data-testid={`budget-section-${title.toLowerCase()}`} className="shadow-sm">
      <CardHeader className="bg-gradient-to-r from-secondary/50 to-transparent border-b border-border/50">
        <CardTitle className="text-lg flex items-center gap-2">
          {isFixed ? (
            <div className="w-2 h-2 rounded-full bg-blue-500" />
          ) : (
            <div className="w-2 h-2 rounded-full bg-amber-500" />
          )}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {items.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">
            No budgets in this category
          </div>
        ) : (
          <div>
            <div className="budget-row bg-secondary/30 text-sm font-medium text-muted-foreground">
              <span>Category</span>
              <span className="text-right">Budget</span>
              <span className="text-right">Actual</span>
              <span className="text-right">Remaining</span>
            </div>
            {items.map((item) => {
              const progressColor = item.percentage > 100 
                ? 'bg-gradient-to-r from-rose-500 to-pink-500' 
                : item.percentage > 80 
                  ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                  : 'bg-gradient-to-r from-emerald-500 to-teal-500';
              
              return (
                <div 
                  key={item.id} 
                  className="budget-row group hover:bg-secondary/50 cursor-pointer transition-colors duration-200"
                  onClick={() => openEdit(item)}
                >
                  <div>
                    <span className="font-medium">{item.category?.category_name || "Unknown"}</span>
                    <div className="mt-1.5 h-2 bg-secondary rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${progressColor}`}
                        style={{ width: `${Math.min(item.percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-right tabular-nums font-medium">{formatCurrency(item.amount)}</span>
                  <span className={`text-right tabular-nums font-medium ${item.percentage > 100 ? 'text-rose-600 dark:text-rose-400' : ''}`}>
                    {formatCurrency(item.spent)}
                  </span>
                  <span className={`text-right tabular-nums font-semibold ${item.remaining < 0 ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                    {formatCurrency(item.remaining)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div data-testid="budget-page">
      <PageHeader
        title="Budget"
        subtitle="Plan and track your spending"
        month={month}
        setMonth={setMonth}
        onMenuClick={onMenuClick}
        actions={
          <Button onClick={openNew} data-testid="add-budget-btn">
            <Plus className="w-4 h-4 mr-2" />
            Add Budget
          </Button>
        }
      />

      <div className="page-content space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card data-testid="income-summary-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Income</CardTitle>
              <TrendingUp className="w-4 h-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                {formatCurrency(income)}
              </div>
            </CardContent>
          </Card>

          <Card data-testid="expenses-summary-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Expenses</CardTitle>
              <TrendingDown className="w-4 h-4 text-rose-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tabular-nums">
                {formatCurrency(expenses)}
              </div>
            </CardContent>
          </Card>

          <Card data-testid="total-budget-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Budget</CardTitle>
              <Target className="w-4 h-4 text-accent" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tabular-nums">
                {formatCurrency(totalBudget)}
              </div>
            </CardContent>
          </Card>

          <Card data-testid="left-to-budget-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Left to Budget</CardTitle>
              <Target className="w-4 h-4 text-accent" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold tabular-nums ${leftToBudget >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                {formatCurrency(leftToBudget)}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Budget Sections */}
        <BudgetSection title="Fixed Expenses" items={fixedBudgets} />
        <BudgetSection title="Flexible Expenses" items={flexibleBudgets} />
      </div>

      {/* Budget Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="budget-dialog">
          <DialogHeader>
            <DialogTitle>{editingBudget ? "Edit Budget" : "Add Budget"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Category</Label>
              <Select
                value={formData.category_id}
                onValueChange={(value) => setFormData((prev) => ({ ...prev, category_id: value }))}
                disabled={!!editingBudget}
              >
                <SelectTrigger data-testid="budget-category-select">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {expenseCategories.map((cat) => (
                    <SelectItem key={cat.id} value={cat.id}>
                      {cat.category_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="amount">Budget Amount</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="0"
                  className="pl-8"
                  value={formData.amount}
                  onChange={(e) => setFormData((prev) => ({ ...prev, amount: e.target.value }))}
                  required
                  data-testid="budget-amount-input"
                />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="rollover">Rollover unused budget</Label>
              <Switch
                id="rollover"
                checked={formData.rollover}
                onCheckedChange={(checked) => setFormData((prev) => ({ ...prev, rollover: checked }))}
                data-testid="budget-rollover-switch"
              />
            </div>
            <DialogFooter className="flex gap-2">
              {editingBudget && (
                <Button 
                  type="button" 
                  variant="destructive" 
                  onClick={() => handleDelete(editingBudget.id)}
                  data-testid="delete-budget-btn"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete
                </Button>
              )}
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" data-testid="save-budget-btn">
                {editingBudget ? "Update" : "Add Budget"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
