import React, { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { User, Users, Tag, Store, Zap, Database, Bell, Shield, Plus, Pencil, Trash2, GripVertical } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { PageHeader } from "../components/layout/PageHeader";
import { useAuth } from "../contexts/AuthContext";
import { useData } from "../contexts/DataContext";
import { toast } from "sonner";

const MEMBER_COLORS = [
  "#3B82F6", "#EC4899", "#10B981", "#F59E0B", "#8B5CF6", "#06B6D4", "#F97316"
];

const timezones = [
  "America/Toronto",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Vancouver",
  "Europe/London",
  "Europe/Paris",
  "Asia/Tokyo",
  "Australia/Sydney",
];

const currencies = ["CAD", "USD", "EUR", "GBP", "AUD", "JPY"];

export default function Settings() {
  const { onMenuClick } = useOutletContext();
  const { api, user, updateUser } = useAuth();
  const { 
    members, categories, merchants, tags, 
    setMembers, setCategories, setMerchants, setTags,
    fetchAll, categoryGroups
  } = useData();
  
  const [activeTab, setActiveTab] = useState("profile");
  const [profileForm, setProfileForm] = useState({
    name: user?.name || "",
    currency: user?.currency || "CAD",
    timezone: user?.timezone || "America/Toronto",
  });
  const [saving, setSaving] = useState(false);

  // Dialogs
  const [memberDialogOpen, setMemberDialogOpen] = useState(false);
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [merchantDialogOpen, setMerchantDialogOpen] = useState(false);
  const [tagDialogOpen, setTagDialogOpen] = useState(false);
  const [ruleDialogOpen, setRuleDialogOpen] = useState(false);

  // Form states
  const [editingMember, setEditingMember] = useState(null);
  const [memberForm, setMemberForm] = useState({ name: "", color: MEMBER_COLORS[0], is_default: false });
  
  const [editingCategory, setEditingCategory] = useState(null);
  const [categoryForm, setCategoryForm] = useState({ group_name: "", category_name: "", type: "expense", is_fixed: false });
  
  const [editingMerchant, setEditingMerchant] = useState(null);
  const [merchantForm, setMerchantForm] = useState({ name: "", default_category_id: "" });
  
  const [tagForm, setTagForm] = useState({ name: "", color: "#64748B" });
  
  const [rules, setRules] = useState([]);
  const [ruleForm, setRuleForm] = useState({ merchant_contains: "", set_category_id: "", set_member_id: "" });

  // Profile handlers
  const handleProfileSave = async () => {
    setSaving(true);
    try {
      await api.put("/auth/settings", profileForm);
      updateUser(profileForm);
      toast.success("Settings saved");
    } catch (error) {
      console.error("Failed to save settings:", error);
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  // Member handlers
  const openMemberDialog = (member = null) => {
    setEditingMember(member);
    setMemberForm(member ? { name: member.name, color: member.color, is_default: member.is_default } : { name: "", color: MEMBER_COLORS[0], is_default: false });
    setMemberDialogOpen(true);
  };

  const saveMember = async (e) => {
    e.preventDefault();
    try {
      if (editingMember) {
        await api.put(`/household-members/${editingMember.id}`, memberForm);
        toast.success("Member updated");
      } else {
        await api.post("/household-members", memberForm);
        toast.success("Member added");
      }
      await fetchAll();
      setMemberDialogOpen(false);
    } catch (error) {
      console.error("Failed to save member:", error);
      toast.error("Failed to save member");
    }
  };

  const deleteMember = async (id) => {
    if (!window.confirm("Delete this member?")) return;
    try {
      await api.delete(`/household-members/${id}`);
      toast.success("Member deleted");
      await fetchAll();
    } catch (error) {
      console.error("Failed to delete member:", error);
      toast.error("Failed to delete member");
    }
  };

  // Category handlers
  const openCategoryDialog = (category = null) => {
    setEditingCategory(category);
    setCategoryForm(category 
      ? { group_name: category.group_name, category_name: category.category_name, type: category.type, is_fixed: category.is_fixed }
      : { group_name: "", category_name: "", type: "expense", is_fixed: false }
    );
    setCategoryDialogOpen(true);
  };

  const saveCategory = async (e) => {
    e.preventDefault();
    try {
      if (editingCategory) {
        await api.put(`/categories/${editingCategory.id}`, categoryForm);
        toast.success("Category updated");
      } else {
        await api.post("/categories", categoryForm);
        toast.success("Category added");
      }
      await fetchAll();
      setCategoryDialogOpen(false);
    } catch (error) {
      console.error("Failed to save category:", error);
      toast.error("Failed to save category");
    }
  };

  const deleteCategory = async (id) => {
    if (!window.confirm("Delete this category?")) return;
    try {
      await api.delete(`/categories/${id}`);
      toast.success("Category deleted");
      await fetchAll();
    } catch (error) {
      console.error("Failed to delete category:", error);
      toast.error("Failed to delete category");
    }
  };

  // Merchant handlers
  const openMerchantDialog = (merchant = null) => {
    setEditingMerchant(merchant);
    setMerchantForm(merchant 
      ? { name: merchant.name, default_category_id: merchant.default_category_id || "" }
      : { name: "", default_category_id: "" }
    );
    setMerchantDialogOpen(true);
  };

  const saveMerchant = async (e) => {
    e.preventDefault();
    try {
      if (editingMerchant) {
        await api.put(`/merchants/${editingMerchant.id}`, merchantForm);
        toast.success("Merchant updated");
      } else {
        await api.post("/merchants", merchantForm);
        toast.success("Merchant added");
      }
      await fetchAll();
      setMerchantDialogOpen(false);
    } catch (error) {
      console.error("Failed to save merchant:", error);
      toast.error("Failed to save merchant");
    }
  };

  const deleteMerchant = async (id) => {
    if (!window.confirm("Delete this merchant?")) return;
    try {
      await api.delete(`/merchants/${id}`);
      toast.success("Merchant deleted");
      await fetchAll();
    } catch (error) {
      console.error("Failed to delete merchant:", error);
      toast.error("Failed to delete merchant");
    }
  };

  // Tag handlers
  const saveTag = async (e) => {
    e.preventDefault();
    try {
      await api.post("/tags", tagForm);
      toast.success("Tag added");
      await fetchAll();
      setTagDialogOpen(false);
      setTagForm({ name: "", color: "#64748B" });
    } catch (error) {
      console.error("Failed to save tag:", error);
      toast.error("Failed to save tag");
    }
  };

  const deleteTag = async (id) => {
    if (!window.confirm("Delete this tag?")) return;
    try {
      await api.delete(`/tags/${id}`);
      toast.success("Tag deleted");
      await fetchAll();
    } catch (error) {
      console.error("Failed to delete tag:", error);
      toast.error("Failed to delete tag");
    }
  };

  // Export handler
  const handleExport = async () => {
    try {
      const response = await api.get("/export/transactions", { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'all-transactions.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("Export downloaded");
    } catch (error) {
      console.error("Export failed:", error);
      toast.error("Failed to export");
    }
  };

  const tabItems = [
    { id: "profile", label: "Profile", icon: User },
    { id: "household", label: "Household", icon: Users },
    { id: "categories", label: "Categories", icon: Tag },
    { id: "merchants", label: "Merchants", icon: Store },
    { id: "tags", label: "Tags", icon: Tag },
    { id: "data", label: "Data", icon: Database },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "security", label: "Security", icon: Shield },
  ];

  return (
    <div data-testid="settings-page">
      <PageHeader
        title="Settings"
        subtitle="Manage your account and preferences"
        showMonthSelector={false}
        onMenuClick={onMenuClick}
      />

      <div className="page-content">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="flex flex-wrap gap-1 h-auto p-1 bg-secondary/50">
            {tabItems.map((tab) => (
              <TabsTrigger 
                key={tab.id} 
                value={tab.id}
                className="flex items-center gap-2 data-[state=active]:bg-card"
                data-testid={`settings-tab-${tab.id}`}
              >
                <tab.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Profile Settings</CardTitle>
                <CardDescription>Manage your personal information</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={profileForm.name}
                    onChange={(e) => setProfileForm(prev => ({ ...prev, name: e.target.value }))}
                    data-testid="profile-name-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Currency</Label>
                  <Select
                    value={profileForm.currency}
                    onValueChange={(value) => setProfileForm(prev => ({ ...prev, currency: value }))}
                  >
                    <SelectTrigger data-testid="profile-currency-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {currencies.map((c) => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Timezone</Label>
                  <Select
                    value={profileForm.timezone}
                    onValueChange={(value) => setProfileForm(prev => ({ ...prev, timezone: value }))}
                  >
                    <SelectTrigger data-testid="profile-timezone-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {timezones.map((tz) => (
                        <SelectItem key={tz} value={tz}>{tz}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleProfileSave} disabled={saving} data-testid="save-profile-btn">
                  {saving ? "Saving..." : "Save Changes"}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Household Tab */}
          <TabsContent value="household" className="mt-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Household Members</CardTitle>
                  <CardDescription>Manage who's in your household</CardDescription>
                </div>
                <Button onClick={() => openMemberDialog()} data-testid="add-member-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Member
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {members.map((member) => (
                    <div 
                      key={member.id} 
                      className="flex items-center justify-between p-3 border border-border rounded-lg"
                      data-testid={`member-${member.id}`}
                    >
                      <div className="flex items-center gap-3">
                        <div 
                          className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
                          style={{ backgroundColor: member.color }}
                        >
                          {member.name.charAt(0)}
                        </div>
                        <div>
                          <p className="font-medium">{member.name}</p>
                          {member.is_default && (
                            <p className="text-xs text-muted-foreground">Default member</p>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" onClick={() => openMemberDialog(member)}>
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="text-destructive hover:text-destructive"
                          onClick={() => deleteMember(member.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Categories Tab */}
          <TabsContent value="categories" className="mt-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Categories</CardTitle>
                  <CardDescription>Manage expense and income categories</CardDescription>
                </div>
                <Button onClick={() => openCategoryDialog()} data-testid="add-category-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Category
                </Button>
              </CardHeader>
              <CardContent>
                {Object.entries(categoryGroups).map(([groupName, cats]) => (
                  <div key={groupName} className="mb-6">
                    <h4 className="font-medium text-sm text-muted-foreground mb-2">{groupName}</h4>
                    <div className="space-y-2">
                      {cats.map((cat) => (
                        <div 
                          key={cat.id} 
                          className="flex items-center justify-between p-2 border border-border rounded-lg"
                        >
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 text-xs rounded ${cat.is_fixed ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}>
                              {cat.is_fixed ? "Fixed" : "Flexible"}
                            </span>
                            <span>{cat.category_name}</span>
                          </div>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="icon" onClick={() => openCategoryDialog(cat)}>
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="text-destructive hover:text-destructive"
                              onClick={() => deleteCategory(cat.id)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Merchants Tab */}
          <TabsContent value="merchants" className="mt-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Merchants</CardTitle>
                  <CardDescription>Manage merchants and default categories</CardDescription>
                </div>
                <Button onClick={() => openMerchantDialog()} data-testid="add-merchant-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Merchant
                </Button>
              </CardHeader>
              <CardContent>
                {merchants.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">No merchants yet</p>
                ) : (
                  <div className="space-y-2">
                    {merchants.map((merchant) => {
                      const defaultCat = categories.find(c => c.id === merchant.default_category_id);
                      return (
                        <div 
                          key={merchant.id} 
                          className="flex items-center justify-between p-3 border border-border rounded-lg"
                        >
                          <div>
                            <p className="font-medium">{merchant.name}</p>
                            {defaultCat && (
                              <p className="text-xs text-muted-foreground">Default: {defaultCat.category_name}</p>
                            )}
                          </div>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="icon" onClick={() => openMerchantDialog(merchant)}>
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="text-destructive hover:text-destructive"
                              onClick={() => deleteMerchant(merchant.id)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tags Tab */}
          <TabsContent value="tags" className="mt-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Tags</CardTitle>
                  <CardDescription>Create tags to organize transactions</CardDescription>
                </div>
                <Button onClick={() => setTagDialogOpen(true)} data-testid="add-tag-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Tag
                </Button>
              </CardHeader>
              <CardContent>
                {tags.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">No tags yet</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {tags.map((tag) => (
                      <div 
                        key={tag.id} 
                        className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-border"
                        style={{ backgroundColor: `${tag.color}10` }}
                      >
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: tag.color }} />
                        <span>{tag.name}</span>
                        <button 
                          className="text-muted-foreground hover:text-destructive"
                          onClick={() => deleteTag(tag.id)}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Data Tab */}
          <TabsContent value="data" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Data Management</CardTitle>
                <CardDescription>Import and export your data</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 border border-border rounded-lg">
                  <h4 className="font-medium mb-2">Export Transactions</h4>
                  <p className="text-sm text-muted-foreground mb-3">Download all your transactions as a CSV file</p>
                  <Button onClick={handleExport} variant="outline" data-testid="export-all-btn">
                    <Database className="w-4 h-4 mr-2" />
                    Export All Transactions
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Notifications</CardTitle>
                <CardDescription>Manage notification preferences</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-center py-8">Notification settings coming soon</p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Security</CardTitle>
                <CardDescription>Manage security settings</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-center py-8">Security settings coming soon</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Member Dialog */}
      <Dialog open={memberDialogOpen} onOpenChange={setMemberDialogOpen}>
        <DialogContent data-testid="member-dialog">
          <DialogHeader>
            <DialogTitle>{editingMember ? "Edit Member" : "Add Member"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={saveMember} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="member_name">Name</Label>
              <Input
                id="member_name"
                value={memberForm.name}
                onChange={(e) => setMemberForm(prev => ({ ...prev, name: e.target.value }))}
                required
                data-testid="member-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Color</Label>
              <div className="flex gap-2 flex-wrap">
                {MEMBER_COLORS.map((color) => (
                  <button
                    key={color}
                    type="button"
                    className={`w-8 h-8 rounded-full transition-transform ${
                      memberForm.color === color ? "ring-2 ring-offset-2 ring-accent scale-110" : ""
                    }`}
                    style={{ backgroundColor: color }}
                    onClick={() => setMemberForm(prev => ({ ...prev, color }))}
                  />
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="is_default">Set as default member</Label>
              <Switch
                id="is_default"
                checked={memberForm.is_default}
                onCheckedChange={(checked) => setMemberForm(prev => ({ ...prev, is_default: checked }))}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setMemberDialogOpen(false)}>Cancel</Button>
              <Button type="submit" data-testid="save-member-btn">{editingMember ? "Update" : "Add"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Category Dialog */}
      <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
        <DialogContent data-testid="category-dialog">
          <DialogHeader>
            <DialogTitle>{editingCategory ? "Edit Category" : "Add Category"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={saveCategory} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="group_name">Group Name</Label>
              <Input
                id="group_name"
                placeholder="e.g., Food, Housing"
                value={categoryForm.group_name}
                onChange={(e) => setCategoryForm(prev => ({ ...prev, group_name: e.target.value }))}
                required
                data-testid="category-group-input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="category_name">Category Name</Label>
              <Input
                id="category_name"
                placeholder="e.g., Groceries, Rent"
                value={categoryForm.category_name}
                onChange={(e) => setCategoryForm(prev => ({ ...prev, category_name: e.target.value }))}
                required
                data-testid="category-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={categoryForm.type}
                onValueChange={(value) => setCategoryForm(prev => ({ ...prev, type: value }))}
              >
                <SelectTrigger data-testid="category-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="expense">Expense</SelectItem>
                  <SelectItem value="income">Income</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="is_fixed">Fixed expense</Label>
              <Switch
                id="is_fixed"
                checked={categoryForm.is_fixed}
                onCheckedChange={(checked) => setCategoryForm(prev => ({ ...prev, is_fixed: checked }))}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCategoryDialogOpen(false)}>Cancel</Button>
              <Button type="submit" data-testid="save-category-btn">{editingCategory ? "Update" : "Add"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Merchant Dialog */}
      <Dialog open={merchantDialogOpen} onOpenChange={setMerchantDialogOpen}>
        <DialogContent data-testid="merchant-dialog">
          <DialogHeader>
            <DialogTitle>{editingMerchant ? "Edit Merchant" : "Add Merchant"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={saveMerchant} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="merchant_name">Merchant Name</Label>
              <Input
                id="merchant_name"
                value={merchantForm.name}
                onChange={(e) => setMerchantForm(prev => ({ ...prev, name: e.target.value }))}
                required
                data-testid="merchant-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Default Category</Label>
              <Select
                value={merchantForm.default_category_id}
                onValueChange={(value) => setMerchantForm(prev => ({ ...prev, default_category_id: value }))}
              >
                <SelectTrigger data-testid="merchant-category-select">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((cat) => (
                    <SelectItem key={cat.id} value={cat.id}>{cat.category_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setMerchantDialogOpen(false)}>Cancel</Button>
              <Button type="submit" data-testid="save-merchant-btn">{editingMerchant ? "Update" : "Add"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Tag Dialog */}
      <Dialog open={tagDialogOpen} onOpenChange={setTagDialogOpen}>
        <DialogContent data-testid="tag-dialog">
          <DialogHeader>
            <DialogTitle>Add Tag</DialogTitle>
          </DialogHeader>
          <form onSubmit={saveTag} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tag_name">Tag Name</Label>
              <Input
                id="tag_name"
                value={tagForm.name}
                onChange={(e) => setTagForm(prev => ({ ...prev, name: e.target.value }))}
                required
                data-testid="tag-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Color</Label>
              <Input
                type="color"
                value={tagForm.color}
                onChange={(e) => setTagForm(prev => ({ ...prev, color: e.target.value }))}
                className="h-10 w-20"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setTagDialogOpen(false)}>Cancel</Button>
              <Button type="submit" data-testid="save-tag-btn">Add Tag</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
