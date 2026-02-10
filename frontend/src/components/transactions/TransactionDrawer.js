import React, { useState, useEffect } from "react";
import { X, Trash2 } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { useData } from "../../contexts/DataContext";
import { useAuth } from "../../contexts/AuthContext";
import { toast } from "sonner";

export const TransactionDrawer = ({ 
  isOpen, 
  onClose, 
  transaction = null, 
  defaultType = "expense",
  onSave 
}) => {
  const { api } = useAuth();
  const { categories, members, accounts, merchants, getDefaultMember, categoryGroups } = useData();
  
  const defaultMember = getDefaultMember();
  
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split("T")[0],
    type: defaultType,
    amount: "",
    merchant_name: "",
    category_id: "",
    account_id: "",
    member_id: defaultMember?.id || "",
    notes: "",
    tags: [],
  });
  
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    if (transaction) {
      setFormData({
        date: transaction.date,
        type: transaction.type,
        amount: Math.abs(transaction.amount).toString(),
        merchant_name: transaction.merchant_name || "",
        category_id: transaction.category_id || "",
        account_id: transaction.account_id || "",
        member_id: transaction.member_id || "",
        notes: transaction.notes || "",
        tags: transaction.tags || [],
      });
    } else {
      setFormData({
        date: new Date().toISOString().split("T")[0],
        type: defaultType,
        amount: "",
        merchant_name: "",
        category_id: "",
        account_id: accounts[0]?.id || "",
        member_id: defaultMember?.id || "",
        notes: "",
        tags: [],
      });
    }
  }, [transaction, defaultType, accounts, defaultMember]);

  const handleMerchantChange = (value) => {
    setFormData((prev) => ({ ...prev, merchant_name: value }));
    
    // Auto-suggest category based on merchant history
    if (value.length > 1) {
      const matchingMerchants = merchants.filter((m) =>
        m.name.toLowerCase().includes(value.toLowerCase())
      );
      setSuggestions(matchingMerchants);
      
      // Auto-fill category if exact match found
      const exactMatch = merchants.find(
        (m) => m.name.toLowerCase() === value.toLowerCase()
      );
      if (exactMatch?.default_category_id && !formData.category_id) {
        setFormData((prev) => ({
          ...prev,
          category_id: exactMatch.default_category_id,
        }));
      }
    } else {
      setSuggestions([]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const amount = parseFloat(formData.amount);
      const finalAmount = formData.type === "expense" ? -Math.abs(amount) : Math.abs(amount);
      
      const payload = {
        ...formData,
        amount: finalAmount,
      };

      if (transaction) {
        await api.put(`/transactions/${transaction.id}`, payload);
        toast.success("Transaction updated");
      } else {
        await api.post("/transactions", payload);
        toast.success("Transaction created");
      }
      
      onSave?.();
      onClose();
    } catch (error) {
      console.error("Failed to save transaction:", error);
      toast.error("Failed to save transaction");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!transaction) return;
    
    if (!window.confirm("Are you sure you want to delete this transaction?")) {
      return;
    }
    
    setLoading(true);
    try {
      await api.delete(`/transactions/${transaction.id}`);
      toast.success("Transaction deleted");
      onSave?.();
      onClose();
    } catch (error) {
      console.error("Failed to delete transaction:", error);
      toast.error("Failed to delete transaction");
    } finally {
      setLoading(false);
    }
  };

  const filteredCategories = formData.type === "income" 
    ? categories.filter((c) => c.type === "income")
    : categories.filter((c) => c.type === "expense");

  if (!isOpen) return null;

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} data-testid="drawer-overlay" />
      <div className="drawer-content" data-testid="transaction-drawer">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold font-['Outfit']">
            {transaction ? "Edit Transaction" : "Add Transaction"}
          </h2>
          <div className="flex items-center gap-2">
            {transaction && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleDelete}
                className="text-destructive hover:text-destructive"
                data-testid="delete-transaction-btn"
              >
                <Trash2 className="w-5 h-5" />
              </Button>
            )}
            <Button variant="ghost" size="icon" onClick={onClose} data-testid="close-drawer-btn">
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Type selector */}
          <div className="flex gap-2 p-1 bg-secondary rounded-lg">
            {["expense", "income", "transfer"].map((type) => (
              <button
                key={type}
                type="button"
                className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                  formData.type === type
                    ? "bg-card shadow-sm text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => setFormData((prev) => ({ ...prev, type }))}
                data-testid={`type-${type}-btn`}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>

          {/* Date */}
          <div className="space-y-2">
            <Label htmlFor="date">Date</Label>
            <Input
              id="date"
              type="date"
              value={formData.date}
              onChange={(e) => setFormData((prev) => ({ ...prev, date: e.target.value }))}
              data-testid="transaction-date-input"
            />
          </div>

          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount">Amount</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                $
              </span>
              <Input
                id="amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                className="pl-8"
                value={formData.amount}
                onChange={(e) => setFormData((prev) => ({ ...prev, amount: e.target.value }))}
                required
                data-testid="transaction-amount-input"
              />
            </div>
          </div>

          {/* Merchant */}
          <div className="space-y-2">
            <Label htmlFor="merchant">Merchant / Description</Label>
            <div className="relative">
              <Input
                id="merchant"
                placeholder="Enter merchant name"
                value={formData.merchant_name}
                onChange={(e) => handleMerchantChange(e.target.value)}
                autoComplete="off"
                data-testid="transaction-merchant-input"
              />
              {suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-lg shadow-lg z-10 max-h-40 overflow-y-auto">
                  {suggestions.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      className="w-full px-3 py-2 text-left text-sm hover:bg-secondary"
                      onClick={() => {
                        setFormData((prev) => ({
                          ...prev,
                          merchant_name: m.name,
                          merchant_id: m.id,
                          category_id: m.default_category_id || prev.category_id,
                        }));
                        setSuggestions([]);
                      }}
                    >
                      {m.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Category */}
          <div className="space-y-2">
            <Label>Category</Label>
            <Select
              value={formData.category_id}
              onValueChange={(value) => setFormData((prev) => ({ ...prev, category_id: value }))}
            >
              <SelectTrigger data-testid="transaction-category-select">
                <SelectValue placeholder="Select category" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(
                  filteredCategories.reduce((acc, cat) => {
                    if (!acc[cat.group_name]) acc[cat.group_name] = [];
                    acc[cat.group_name].push(cat);
                    return acc;
                  }, {})
                ).map(([group, cats]) => (
                  <div key={group}>
                    <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                      {group}
                    </div>
                    {cats.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>
                        {cat.category_name}
                      </SelectItem>
                    ))}
                  </div>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Account */}
          <div className="space-y-2">
            <Label>Account</Label>
            <Select
              value={formData.account_id}
              onValueChange={(value) => setFormData((prev) => ({ ...prev, account_id: value }))}
            >
              <SelectTrigger data-testid="transaction-account-select">
                <SelectValue placeholder="Select account" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((acc) => (
                  <SelectItem key={acc.id} value={acc.id}>
                    {acc.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Member */}
          <div className="space-y-2">
            <Label>Household Member</Label>
            <Select
              value={formData.member_id}
              onValueChange={(value) => setFormData((prev) => ({ ...prev, member_id: value }))}
            >
              <SelectTrigger data-testid="transaction-member-select">
                <SelectValue placeholder="Select member" />
              </SelectTrigger>
              <SelectContent>
                {members.map((mem) => (
                  <SelectItem key={mem.id} value={mem.id}>
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: mem.color }}
                      />
                      {mem.name}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              placeholder="Add notes..."
              value={formData.notes}
              onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
              rows={3}
              data-testid="transaction-notes-input"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              onClick={onClose}
              data-testid="cancel-transaction-btn"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              disabled={loading}
              data-testid="save-transaction-btn"
            >
              {loading ? "Saving..." : transaction ? "Update" : "Add Transaction"}
            </Button>
          </div>
        </form>
      </div>
    </>
  );
};
