import React, { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Plus, Building2, PiggyBank, CreditCard, Wallet, Landmark, Banknote, Pencil, Trash2 } from "lucide-react";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { PageHeader } from "../components/layout/PageHeader";
import { useAuth } from "../contexts/AuthContext";
import { useData } from "../contexts/DataContext";
import { formatCurrency } from "../lib/utils";
import { toast } from "sonner";

const accountIcons = {
  checking: Building2,
  savings: PiggyBank,
  credit: CreditCard,
  cash: Wallet,
  loan: Landmark,
  other: Banknote,
};

const accountTypes = [
  { value: "checking", label: "Checking" },
  { value: "savings", label: "Savings" },
  { value: "credit", label: "Credit Card" },
  { value: "cash", label: "Cash" },
  { value: "loan", label: "Loan" },
  { value: "other", label: "Other" },
];

export default function Accounts() {
  const { onMenuClick } = useOutletContext();
  const { api } = useAuth();
  const { accounts, setAccounts, fetchAll } = useData();
  
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    type: "checking",
    opening_balance: "0",
  });
  const [loading, setLoading] = useState(false);

  const totalBalance = accounts.reduce((sum, acc) => sum + (acc.current_balance || 0), 0);
  const totalAssets = accounts
    .filter(a => a.type !== "credit" && a.type !== "loan")
    .reduce((sum, acc) => sum + (acc.current_balance || 0), 0);
  const totalLiabilities = accounts
    .filter(a => a.type === "credit" || a.type === "loan")
    .reduce((sum, acc) => sum + Math.abs(acc.current_balance || 0), 0);

  const openNew = () => {
    setEditingAccount(null);
    setFormData({ name: "", type: "checking", opening_balance: "0" });
    setDialogOpen(true);
  };

  const openEdit = (account) => {
    setEditingAccount(account);
    setFormData({
      name: account.name,
      type: account.type,
      opening_balance: account.opening_balance.toString(),
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        opening_balance: parseFloat(formData.opening_balance),
      };

      if (editingAccount) {
        await api.put(`/accounts/${editingAccount.id}`, payload);
        toast.success("Account updated");
      } else {
        await api.post("/accounts", payload);
        toast.success("Account created");
      }
      
      await fetchAll();
      setDialogOpen(false);
    } catch (error) {
      console.error("Failed to save account:", error);
      toast.error("Failed to save account");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (accountId) => {
    if (!window.confirm("Are you sure you want to delete this account?")) {
      return;
    }

    try {
      await api.delete(`/accounts/${accountId}`);
      toast.success("Account deleted");
      await fetchAll();
    } catch (error) {
      console.error("Failed to delete account:", error);
      toast.error("Failed to delete account");
    }
  };

  return (
    <div data-testid="accounts-page">
      <PageHeader
        title="Accounts"
        subtitle="Manage your financial accounts"
        showMonthSelector={false}
        onMenuClick={onMenuClick}
        actions={
          <Button onClick={openNew} data-testid="add-account-btn">
            <Plus className="w-4 h-4 mr-2" />
            Add Account
          </Button>
        }
      />

      <div className="page-content space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card data-testid="total-balance-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Net Worth</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold tabular-nums ${totalBalance >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                {formatCurrency(totalBalance)}
              </div>
            </CardContent>
          </Card>
          
          <Card data-testid="total-assets-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Assets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                {formatCurrency(totalAssets)}
              </div>
            </CardContent>
          </Card>
          
          <Card data-testid="total-liabilities-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Liabilities</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-rose-600 dark:text-rose-400 tabular-nums">
                {formatCurrency(totalLiabilities)}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Accounts List */}
        <Card data-testid="accounts-list">
          <CardHeader>
            <CardTitle>All Accounts</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {accounts.length === 0 ? (
              <div className="empty-state">
                <Wallet className="empty-state-icon" />
                <h3 className="text-lg font-medium">No accounts yet</h3>
                <p className="text-muted-foreground mt-1">Add an account to start tracking your finances</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {accounts.map((account) => {
                  const Icon = accountIcons[account.type] || Banknote;
                  const isLiability = account.type === "credit" || account.type === "loan";
                  
                  return (
                    <div 
                      key={account.id} 
                      className="px-4 py-4 flex items-center justify-between hover:bg-secondary/30 transition-colors"
                      data-testid={`account-${account.id}`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                          isLiability ? 'bg-rose-100 dark:bg-rose-900/30' : 'bg-accent/10'
                        }`}>
                          <Icon className={`w-5 h-5 ${isLiability ? 'text-rose-600 dark:text-rose-400' : 'text-accent'}`} />
                        </div>
                        <div>
                          <h4 className="font-medium">{account.name}</h4>
                          <p className="text-sm text-muted-foreground capitalize">{account.type}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className={`font-semibold tabular-nums ${
                          (account.current_balance || 0) >= 0 
                            ? 'text-emerald-600 dark:text-emerald-400' 
                            : 'text-rose-600 dark:text-rose-400'
                        }`}>
                          {formatCurrency(account.current_balance || 0)}
                        </span>
                        <div className="flex items-center gap-1">
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            onClick={() => openEdit(account)}
                            data-testid={`edit-account-${account.id}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="icon"
                            className="text-destructive hover:text-destructive"
                            onClick={() => handleDelete(account.id)}
                            data-testid={`delete-account-${account.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Account Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="account-dialog">
          <DialogHeader>
            <DialogTitle>{editingAccount ? "Edit Account" : "Add Account"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Account Name</Label>
              <Input
                id="name"
                placeholder="e.g., Main Checking"
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                required
                data-testid="account-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Account Type</Label>
              <Select
                value={formData.type}
                onValueChange={(value) => setFormData((prev) => ({ ...prev, type: value }))}
              >
                <SelectTrigger data-testid="account-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {accountTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="balance">Opening Balance</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  id="balance"
                  type="number"
                  step="0.01"
                  className="pl-8"
                  value={formData.opening_balance}
                  onChange={(e) => setFormData((prev) => ({ ...prev, opening_balance: e.target.value }))}
                  required
                  data-testid="account-balance-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={loading} data-testid="save-account-btn">
                {loading ? "Saving..." : editingAccount ? "Update" : "Add Account"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
