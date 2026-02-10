import React, { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Plus, Flag, Pencil, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Progress } from "../components/ui/progress";
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
import { formatCurrency, formatDate } from "../lib/utils";
import { toast } from "sonner";

const GOAL_COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#06B6D4", "#F97316", "#6366F1"
];

export default function Goals() {
  const { onMenuClick } = useOutletContext();
  const { api } = useAuth();
  const { goals, setGoals, fetchAll } = useData();
  
  const [dialogOpen, setDialogOpen] = useState(false);
  const [contributeDialogOpen, setContributeDialogOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState(null);
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [contributeAmount, setContributeAmount] = useState("");
  const [formData, setFormData] = useState({
    name: "",
    target_amount: "",
    target_date: "",
    current_amount: "0",
    color: GOAL_COLORS[0],
  });

  const totalTarget = goals.reduce((sum, g) => sum + g.target_amount, 0);
  const totalCurrent = goals.reduce((sum, g) => sum + g.current_amount, 0);
  const overallProgress = totalTarget > 0 ? (totalCurrent / totalTarget) * 100 : 0;

  const openNew = () => {
    setEditingGoal(null);
    setFormData({
      name: "",
      target_amount: "",
      target_date: "",
      current_amount: "0",
      color: GOAL_COLORS[Math.floor(Math.random() * GOAL_COLORS.length)],
    });
    setDialogOpen(true);
  };

  const openEdit = (goal) => {
    setEditingGoal(goal);
    setFormData({
      name: goal.name,
      target_amount: goal.target_amount.toString(),
      target_date: goal.target_date || "",
      current_amount: goal.current_amount.toString(),
      color: goal.color,
    });
    setDialogOpen(true);
  };

  const openContribute = (goal) => {
    setSelectedGoal(goal);
    setContributeAmount("");
    setContributeDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name: formData.name,
        target_amount: parseFloat(formData.target_amount),
        target_date: formData.target_date || null,
        current_amount: parseFloat(formData.current_amount),
        color: formData.color,
      };

      if (editingGoal) {
        await api.put(`/goals/${editingGoal.id}`, payload);
        toast.success("Goal updated");
      } else {
        await api.post("/goals", payload);
        toast.success("Goal created");
      }
      
      await fetchAll();
      setDialogOpen(false);
    } catch (error) {
      console.error("Failed to save goal:", error);
      toast.error("Failed to save goal");
    }
  };

  const handleContribute = async (e) => {
    e.preventDefault();
    if (!selectedGoal) return;

    try {
      await api.post(`/goals/${selectedGoal.id}/contribute?amount=${parseFloat(contributeAmount)}`);
      toast.success("Contribution added");
      await fetchAll();
      setContributeDialogOpen(false);
    } catch (error) {
      console.error("Failed to add contribution:", error);
      toast.error("Failed to add contribution");
    }
  };

  const handleDelete = async (goalId) => {
    if (!window.confirm("Delete this goal?")) return;
    
    try {
      await api.delete(`/goals/${goalId}`);
      toast.success("Goal deleted");
      await fetchAll();
    } catch (error) {
      console.error("Failed to delete goal:", error);
      toast.error("Failed to delete goal");
    }
  };

  return (
    <div data-testid="goals-page">
      <PageHeader
        title="Goals"
        subtitle="Track your savings goals"
        showMonthSelector={false}
        onMenuClick={onMenuClick}
        actions={
          <Button onClick={openNew} data-testid="add-goal-btn">
            <Plus className="w-4 h-4 mr-2" />
            Add Goal
          </Button>
        }
      />

      <div className="page-content space-y-6">
        {/* Summary */}
        <Card data-testid="goals-summary-card">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold">Overall Progress</h3>
                <p className="text-muted-foreground">
                  {formatCurrency(totalCurrent)} of {formatCurrency(totalTarget)} saved
                </p>
              </div>
              <div className="flex-1 max-w-md">
                <Progress value={Math.min(overallProgress, 100)} className="h-3" />
                <p className="text-sm text-muted-foreground mt-1 text-right">
                  {overallProgress.toFixed(1)}% complete
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Goals Grid */}
        {goals.length === 0 ? (
          <Card>
            <CardContent className="empty-state">
              <Flag className="empty-state-icon" />
              <h3 className="text-lg font-medium">No goals yet</h3>
              <p className="text-muted-foreground mt-1">Create a goal to start tracking your savings</p>
              <Button onClick={openNew} className="mt-4">
                <Plus className="w-4 h-4 mr-2" />
                Create Your First Goal
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {goals.map((goal) => {
              const progress = (goal.current_amount / goal.target_amount) * 100;
              const remaining = goal.target_amount - goal.current_amount;
              
              return (
                <Card 
                  key={goal.id} 
                  className="overflow-hidden group"
                  data-testid={`goal-${goal.id}`}
                >
                  <div 
                    className="h-2"
                    style={{ backgroundColor: goal.color }}
                  />
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div 
                          className="w-12 h-12 rounded-xl flex items-center justify-center"
                          style={{ backgroundColor: `${goal.color}20` }}
                        >
                          <Flag className="w-6 h-6" style={{ color: goal.color }} />
                        </div>
                        <div>
                          <h4 className="font-semibold">{goal.name}</h4>
                          {goal.target_date && (
                            <p className="text-xs text-muted-foreground">
                              Target: {formatDate(goal.target_date)}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button 
                          variant="ghost" 
                          size="icon"
                          onClick={() => openEdit(goal)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleDelete(goal.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>

                    <div className="mb-4">
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-muted-foreground">Progress</span>
                        <span className="font-medium">{progress.toFixed(0)}%</span>
                      </div>
                      <Progress 
                        value={Math.min(progress, 100)} 
                        className="h-2"
                        style={{ '--progress-color': goal.color }}
                      />
                    </div>

                    <div className="flex justify-between text-sm mb-4">
                      <div>
                        <p className="text-muted-foreground">Saved</p>
                        <p className="font-semibold" style={{ color: goal.color }}>
                          {formatCurrency(goal.current_amount)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-muted-foreground">Remaining</p>
                        <p className="font-semibold">
                          {formatCurrency(Math.max(remaining, 0))}
                        </p>
                      </div>
                    </div>

                    <Button 
                      className="w-full"
                      variant="outline"
                      onClick={() => openContribute(goal)}
                      data-testid={`contribute-${goal.id}`}
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Add Contribution
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Goal Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="goal-dialog">
          <DialogHeader>
            <DialogTitle>{editingGoal ? "Edit Goal" : "Add Goal"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Goal Name</Label>
              <Input
                id="name"
                placeholder="e.g., Vacation Fund"
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                required
                data-testid="goal-name-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="target">Target Amount</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                  <Input
                    id="target"
                    type="number"
                    step="0.01"
                    min="0"
                    className="pl-8"
                    value={formData.target_amount}
                    onChange={(e) => setFormData((prev) => ({ ...prev, target_amount: e.target.value }))}
                    required
                    data-testid="goal-target-input"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="current">Current Amount</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                  <Input
                    id="current"
                    type="number"
                    step="0.01"
                    min="0"
                    className="pl-8"
                    value={formData.current_amount}
                    onChange={(e) => setFormData((prev) => ({ ...prev, current_amount: e.target.value }))}
                    data-testid="goal-current-input"
                  />
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="target_date">Target Date (optional)</Label>
              <Input
                id="target_date"
                type="date"
                value={formData.target_date}
                onChange={(e) => setFormData((prev) => ({ ...prev, target_date: e.target.value }))}
                data-testid="goal-date-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Color</Label>
              <div className="flex gap-2 flex-wrap">
                {GOAL_COLORS.map((color) => (
                  <button
                    key={color}
                    type="button"
                    className={`w-8 h-8 rounded-full transition-transform ${
                      formData.color === color ? "ring-2 ring-offset-2 ring-accent scale-110" : ""
                    }`}
                    style={{ backgroundColor: color }}
                    onClick={() => setFormData((prev) => ({ ...prev, color }))}
                  />
                ))}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" data-testid="save-goal-btn">
                {editingGoal ? "Update" : "Create Goal"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Contribute Dialog */}
      <Dialog open={contributeDialogOpen} onOpenChange={setContributeDialogOpen}>
        <DialogContent data-testid="contribute-dialog">
          <DialogHeader>
            <DialogTitle>Add Contribution to {selectedGoal?.name}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleContribute} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="contribute_amount">Amount</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  id="contribute_amount"
                  type="number"
                  step="0.01"
                  min="0"
                  className="pl-8"
                  value={contributeAmount}
                  onChange={(e) => setContributeAmount(e.target.value)}
                  required
                  data-testid="contribute-amount-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setContributeDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" data-testid="save-contribution-btn">
                Add Contribution
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
