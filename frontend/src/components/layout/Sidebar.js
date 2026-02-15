import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { 
  LayoutDashboard, 
  Wallet, 
  ArrowLeftRight, 
  TrendingUp, 
  PieChart, 
  Target as TargetIcon, 
  RefreshCw, 
  Flag, 
  Settings,
  LogOut,
  Moon,
  Sun,
  X,
  Brain
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { Button } from "../ui/button";
import { cn } from "../../lib/utils";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/accounts", label: "Accounts", icon: Wallet },
  { path: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { path: "/cash-flow", label: "Cash Flow", icon: TrendingUp },
  { path: "/reports", label: "Reports", icon: PieChart },
  { path: "/budget", label: "Budget", icon: TargetIcon },
  { path: "/recurring", label: "Recurring", icon: RefreshCw },
  { path: "/goals", label: "Goals", icon: Flag },
  { path: "/insights", label: "AI Insights", icon: Brain, highlight: true },
  { path: "/settings", label: "Settings", icon: Settings },
];

export const Sidebar = ({ isOpen, onClose }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
          data-testid="sidebar-overlay"
        />
      )}
      
      <aside 
        className={cn(
          "app-sidebar",
          isOpen && "open"
        )}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-accent flex items-center justify-center">
              <Wallet className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-lg font-['Outfit']">Expense Tracker</span>
          </div>
          <button 
            className="md:hidden p-1.5 hover:bg-secondary rounded-lg"
            onClick={onClose}
            data-testid="close-sidebar-btn"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  onClick={onClose}
                  className={({ isActive }) =>
                    cn(
                      "sidebar-item", 
                      isActive && "active",
                      item.highlight && "bg-gradient-to-r from-violet-500/10 to-purple-500/10 border border-violet-500/20"
                    )
                  }
                  data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
                >
                  <item.icon className={cn("w-5 h-5", item.highlight && "text-violet-500")} />
                  <span className={item.highlight ? "text-violet-600 dark:text-violet-400 font-medium" : ""}>
                    {item.label}
                  </span>
                  {item.highlight && (
                    <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full bg-violet-500 text-white font-medium">
                      NEW
                    </span>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Bottom section */}
        <div className="p-4 border-t border-border space-y-3">
          {/* Theme toggle */}
          <Button
            variant="ghost"
            className="w-full justify-start gap-3"
            onClick={toggleTheme}
            data-testid="theme-toggle-btn"
          >
            {theme === "dark" ? (
              <>
                <Sun className="w-5 h-5" />
                <span>Light Mode</span>
              </>
            ) : (
              <>
                <Moon className="w-5 h-5" />
                <span>Dark Mode</span>
              </>
            )}
          </Button>

          {/* User info & logout */}
          <div className="flex items-center justify-between px-3 py-2 bg-secondary/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center">
                <span className="text-sm font-medium text-accent">
                  {user?.name?.charAt(0) || "U"}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.name}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              className="shrink-0"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </aside>
    </>
  );
};
