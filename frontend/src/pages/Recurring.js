import React, { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Plus, RefreshCw, Calendar, Play, Pencil, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
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
import { formatCurrency, formatShortDate, getCurrentMonth, getMemberColor } from "../lib/utils";
import { toast } from "sonner";

const frequencies = [
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Bi-weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "yearly", label: "Yearly" },
];

export default function Recurring() {
  const { onMenuClick } = useOutletContext();
  const { api } = useAuth();
  const { categories, members, accounts, getCategoryById, getMemberById, getAccountById, expenseCategories, incomeCategories } = useData();
  
  const [month, setMonth] = useState(getCurrentMonth());
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    type: "expense",
    amount: "",
    frequency: "monthly",
    next_date: new Date().toISOString().split("T")[0],
    category_id: "",
    account_id: "",
    member_id: "",
    autopost: false,
    notes: "",
  });

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const response = await api.get("/recurring");
      setRules(response.data);
    } catch (error) {
      console.error("Failed to fetch recurring rules:", error);
    } finally {
      setLoading(false);
    }
  };

  const incomeRules = rules.filter(r => r.type === "income");
  const expenseRules = rules.filter(r => r.type === "expense");
  const upcomingRules = rules.filter(r => r.next_date.startsWith(month));

  const openNew = (type = "expense") => {
    setEditingRule(null);
    setFormData({
      name: "",
      type,
      amount: "",
      frequency: "monthly",
      next_date: new Date().toISOString().split("T")[0],
      category_id: "",
      account_id: accounts[0]?.id || "",
      member_id: members.find(m => m.is_default)?.id || members[0]?.id || "",
      autopost: false,
      notes: "",
    });
    setDialogOpen(true);
  };

  const openEdit = (rule) => {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      type: rule.type,
      amount: Math.abs(rule.amount).toString(),
      frequency: rule.frequency,
      next_date: rule.next_date,
      category_id: rule.category_id || "",
      account_id: rule.account_id || "",
      member_id: rule.member_id || "",
      autopost: rule.autopost,
      notes: rule.notes || "",
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const amount = parseFloat(formData.amount);
      const payload = {
        ...formData,
        amount: formData.type === "expense" ? -Math.abs(amount) : Math.abs(amount),
      };

      if (editingRule) {
        await api.put(`/recurring/${editingRule.id}`, payload);
        toast.success("Recurring rule updated");
      } else {
        await api.post("/recurring", payload);
        toast.success("Recurring rule created");
      }
      
      await fetchRules();
      setDialogOpen(false);
    } catch (error) {
      console.error("Failed to save recurring rule:", error);
      toast.error("Failed to save recurring rule");
    }
  };

  const handleDelete = async (ruleId) => {
    if (!window.confirm("Delete this recurring rule?")) return;
    
    try {
      await api.delete(`/recurring/${ruleId}`);
      toast.success("Recurring rule deleted");
      await fetchRules();
    } catch (error) {
      console.error("Failed to delete recurring rule:", error);
      toast.error("Failed to delete recurring rule");
    }
  };

  const handlePost = async (ruleId) => {
    try {
      await api.post(`/recurring/${ruleId}/post`);
      toast.success("Transaction posted");
      await fetchRules();
    } catch (error) {
      console.error("Failed to post transaction:", error);
      toast.error("Failed to post transaction");
    }
  };

  const handleEnableAllAutopost = async () => {
    try {
      const response = await api.post("/migrate/enable-autopost");
      toast.success(response.data.message);
      await fetchRules();
      // Trigger autopost to create due transactions
      await api.post("/recurring/process-autopost");
      toast.success("Due transactions have been auto-posted!");
    } catch (error) {
      console.error("Failed to enable autopost:", error);
      toast.error("Failed to enable autopost");
    }
  };

  const RuleCard = ({ rule }) => {
    const member = getMemberById(rule.member_id);
    const category = getCategoryById(rule.category_id);
    const account = getAccountById(rule.account_id);
    const memberColors = getMemberColor(member?.name);
    const isIncome = rule.type === "income";

    return (
      <div 
        className="p-4 border border-border rounded-xl hover:shadow-md transition-shadow cursor-pointer group"
        onClick={() => openEdit(rule)}
        data-testid={`recurring-${rule.id}`}
      >
        <div className="flex items-start justify-between mb-3">
          <div>
            <h4 className="font-medium">{rule.name}</h4>
            <p className="text-sm text-muted-foreground">
              {category?.category_name || "Uncategorized"}
            </p>
          </div>
          <span className={`font-semibold tabular-nums ${isIncome ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>
            {formatCurrency(Math.abs(rule.amount))}
          </span>
        </div>
        
        <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
          <span className="px-2 py-1 rounded bg-secondary capitalize">{rule.frequency}</span>
          <span className="px-2 py-1 rounded bg-secondary">
            Next: {formatShortDate(rule.next_date)}
          </span>
          {member && (
            <span className={`px-2 py-1 rounded ${memberColors.bg} ${memberColors.text}`}>
              {member.name}
            </span>
          )}
          {rule.autopost && (
            <span className="px-2 py-1 rounded bg-accent/10 text-accent">Auto</span>
          )}
        </div>

        <div className="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button 
            size="sm" 
            variant="outline" 
            onClick={(e) => {
              e.stopPropagation();
              handlePost(rule.id);
            }}
            data-testid={`post-recurring-${rule.id}`}
          >
            <Play className="w-3 h-3 mr-1" />
            Post Now
          </Button>
          <Button 
            size="sm" 
            variant="ghost"
            className="text-destructive hover:text-destructive"
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(rule.id);
            }}
            data-testid={`delete-recurring-${rule.id}`}
          >
            <Trash2 className="w-3 h-3" />
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div data-testid="recurring-page">
      <PageHeader
        title="Recurring"
        subtitle="Manage recurring income and expenses"
        month={month}
        setMonth={setMonth}
        onMenuClick={onMenuClick}
        actions={
          <div className="flex gap-2">
            {rules.some(r => !r.autopost) && (
              <Button variant="outline" onClick={handleEnableAllAutopost} data-testid="enable-autopost-btn">
                <RefreshCw className="w-4 h-4 mr-2" />
                Enable Auto-post All
              </Button>
            )}
            <Button onClick={() => openNew("expense")} data-testid="add-recurring-btn">
              <Plus className="w-4 h-4 mr-2" />
              Add Recurring
            </Button>
          </div>
        }
      />

      <div className="page-content space-y-6">
        {/* Upcoming Due */}
        <Card data-testid="upcoming-due-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Upcoming Due This Month
            </CardTitle>
          </CardHeader>
          <CardContent>
            {upcomingRules.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">No recurring items due this month</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {upcomingRules.map((rule) => (
                  <RuleCard key={rule.id} rule={rule} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recurring Income */}
          <Card data-testid="recurring-income-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Recurring Income</CardTitle>
              <Button size="sm" variant="outline" onClick={() => openNew("income")}>
                <Plus className="w-4 h-4 mr-1" />
                Add
              </Button>
            </CardHeader>
            <CardContent>
              {incomeRules.length === 0 ? (
                <p className="text-muted-foreground text-center py-4">No recurring income set up</p>
              ) : (
                <div className="space-y-3">
                  {incomeRules.map((rule) => (
                    <RuleCard key={rule.id} rule={rule} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recurring Expenses */}
          <Card data-testid="recurring-expenses-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Recurring Expenses</CardTitle>
              <Button size="sm" variant="outline" onClick={() => openNew("expense")}>
                <Plus className="w-4 h-4 mr-1" />
                Add
              </Button>
            </CardHeader>
            <CardContent>
              {expenseRules.length === 0 ? (
                <p className="text-muted-foreground text-center py-4">No recurring expenses set up</p>
              ) : (
                <div className="space-y-3">
                  {expenseRules.map((rule) => (
                    <RuleCard key={rule.id} rule={rule} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg" data-testid="recurring-dialog">
          <DialogHeader>
            <DialogTitle>{editingRule ? "Edit Recurring" : "Add Recurring"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex gap-2 p-1 bg-secondary rounded-lg">
              {["expense", "income"].map((type) => (
                <button
                  key={type}
                  type="button"
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                    formData.type === type
                      ? "bg-card shadow-sm text-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  onClick={() => setFormData((prev) => ({ ...prev, type }))}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="e.g., Monthly Rent"
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                required
                data-testid="recurring-name-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="amount">Amount</Label>
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
                    data-testid="recurring-amount-input"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Frequency</Label>
                <Select
                  value={formData.frequency}
                  onValueChange={(value) => setFormData((prev) => ({ ...prev, frequency: value }))}
                >
                  <SelectTrigger data-testid="recurring-frequency-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {frequencies.map((f) => (
                      <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="next_date">Next Due Date</Label>
              <Input
                id="next_date"
                type="date"
                value={formData.next_date}
                onChange={(e) => setFormData((prev) => ({ ...prev, next_date: e.target.value }))}
                required
                data-testid="recurring-date-input"
              />
            </div>

            <div className="space-y-2">
              <Label>Category</Label>
              <Select
                value={formData.category_id}
                onValueChange={(value) => setFormData((prev) => ({ ...prev, category_id: value }))}
              >
                <SelectTrigger data-testid="recurring-category-select">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {(formData.type === "income" ? incomeCategories : expenseCategories).map((cat) => (
                    <SelectItem key={cat.id} value={cat.id}>{cat.category_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Account</Label>
                <Select
                  value={formData.account_id}
                  onValueChange={(value) => setFormData((prev) => ({ ...prev, account_id: value }))}
                >
                  <SelectTrigger data-testid="recurring-account-select">
                    <SelectValue placeholder="Select account" />
                  </SelectTrigger>
                  <SelectContent>
                    {accounts.map((a) => (
                      <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Member</Label>
                <Select
                  value={formData.member_id}
                  onValueChange={(value) => setFormData((prev) => ({ ...prev, member_id: value }))}
                >
                  <SelectTrigger data-testid="recurring-member-select">
                    <SelectValue placeholder="Select member" />
                  </SelectTrigger>
                  <SelectContent>
                    {members.map((m) => (
                      <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="autopost">Auto-post transactions</Label>
              <Switch
                id="autopost"
                checked={formData.autopost}
                onCheckedChange={(checked) => setFormData((prev) => ({ ...prev, autopost: checked }))}
                data-testid="recurring-autopost-switch"
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" data-testid="save-recurring-btn">
                {editingRule ? "Update" : "Add Recurring"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
