import React from "react";
import { ChevronLeft, ChevronRight, Menu } from "lucide-react";
import { Button } from "../ui/button";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "../ui/select";
import { getMonthName, getPreviousMonth, getNextMonth, getCurrentMonth } from "../../lib/utils";

export const PageHeader = ({ 
  title, 
  subtitle,
  month, 
  setMonth, 
  showMonthSelector = true,
  actions,
  onMenuClick
}) => {
  const months = [];
  const currentMonth = getCurrentMonth();
  const [currentYear, currentMon] = currentMonth.split("-").map(Number);
  
  // Generate last 12 months and next 6 months
  for (let i = -12; i <= 6; i++) {
    const date = new Date(currentYear, currentMon - 1 + i, 1);
    const monthStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    months.push(monthStr);
  }

  return (
    <header className="page-header" data-testid="page-header">
      <div className="flex items-center gap-4">
        <button 
          className="md:hidden p-2 hover:bg-secondary rounded-lg"
          onClick={onMenuClick}
          data-testid="menu-btn"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-semibold font-['Outfit'] tracking-tight">{title}</h1>
          {subtitle && (
            <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {showMonthSelector && month && setMonth && (
          <div className="flex items-center gap-1 bg-secondary/50 rounded-lg p-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setMonth(getPreviousMonth(month))}
              data-testid="prev-month-btn"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            
            <Select value={month} onValueChange={setMonth}>
              <SelectTrigger 
                className="w-[160px] border-0 bg-transparent h-8 focus:ring-0"
                data-testid="month-selector"
              >
                <SelectValue>{getMonthName(month)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {months.map((m) => (
                  <SelectItem key={m} value={m}>
                    {getMonthName(m)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setMonth(getNextMonth(month))}
              data-testid="next-month-btn"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        )}
        
        {actions}
      </div>
    </header>
  );
};
