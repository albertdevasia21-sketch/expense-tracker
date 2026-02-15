import React, { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { 
  Brain, 
  TrendingUp, 
  TrendingDown, 
  PiggyBank, 
  Target, 
  Sparkles,
  RefreshCw,
  ChevronRight,
  Lightbulb,
  BarChart3,
  Wallet,
  Calendar
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { PageHeader } from "../components/layout/PageHeader";
import { useAuth } from "../contexts/AuthContext";
import { formatCurrency, getCurrentMonth } from "../lib/utils";
import { toast } from "sonner";

const InsightCard = ({ title, icon: Icon, color, onClick, loading, description }) => (
  <Card 
    className={`cursor-pointer transition-all hover:shadow-lg hover:scale-[1.02] border-l-4 ${color}`}
    onClick={onClick}
    data-testid={`insight-card-${title.toLowerCase().replace(/\s+/g, '-')}`}
  >
    <CardContent className="p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl bg-gradient-to-br ${color.replace('border-l-', 'from-').replace('-500', '-500/20')} to-transparent`}>
            <Icon className={`w-5 h-5 ${color.replace('border-l-', 'text-')}`} />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">{title}</h3>
            <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
          </div>
        </div>
        {loading ? (
          <RefreshCw className="w-4 h-4 animate-spin text-muted-foreground" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        )}
      </div>
    </CardContent>
  </Card>
);

const StatCard = ({ title, value, change, changeType, icon: Icon, color }) => (
  <Card className="overflow-hidden">
    <CardContent className="p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {change !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-sm ${
          changeType === 'positive' ? 'text-emerald-600' : 
          changeType === 'negative' ? 'text-rose-600' : 'text-muted-foreground'
        }`}>
          {changeType === 'positive' ? <TrendingUp className="w-3 h-3" /> : 
           changeType === 'negative' ? <TrendingDown className="w-3 h-3" /> : null}
          <span>{change}</span>
        </div>
      )}
    </CardContent>
  </Card>
);

export default function Insights() {
  const { onMenuClick } = useOutletContext();
  const { api } = useAuth();
  
  const [month, setMonth] = useState(getCurrentMonth());
  const [quickStats, setQuickStats] = useState(null);
  const [activeInsight, setActiveInsight] = useState(null);
  const [insightContent, setInsightContent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingType, setLoadingType] = useState(null);

  useEffect(() => {
    fetchQuickStats();
  }, [month]);

  const fetchQuickStats = async () => {
    try {
      const response = await api.get(`/insights/quick-stats?month=${month}`);
      setQuickStats(response.data);
    } catch (error) {
      console.error("Failed to fetch quick stats:", error);
    }
  };

  const generateInsight = async (insightType) => {
    setLoadingType(insightType);
    setLoading(true);
    setActiveInsight(insightType);
    setInsightContent(null);
    
    try {
      const response = await api.post("/insights/generate", {
        month,
        insight_type: insightType
      });
      setInsightContent(response.data);
      toast.success("Insight generated successfully!");
    } catch (error) {
      console.error("Failed to generate insight:", error);
      toast.error("Failed to generate insight. Please try again.");
      setActiveInsight(null);
    } finally {
      setLoading(false);
      setLoadingType(null);
    }
  };

  const insightTypes = [
    {
      type: "spending_patterns",
      title: "Spending Patterns",
      icon: BarChart3,
      color: "border-l-violet-500",
      description: "Analyze your spending habits and trends"
    },
    {
      type: "budget_recommendations",
      title: "Budget Recommendations",
      icon: Target,
      color: "border-l-blue-500",
      description: "Get personalized budget adjustments"
    },
    {
      type: "savings_opportunities",
      title: "Savings Opportunities",
      icon: PiggyBank,
      color: "border-l-emerald-500",
      description: "Discover ways to save more money"
    },
    {
      type: "monthly_summary",
      title: "Monthly Summary",
      icon: Calendar,
      color: "border-l-amber-500",
      description: "Complete financial health overview"
    }
  ];

  const formatInsightContent = (content) => {
    if (!content) return null;
    
    // Split by lines and format
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      if (line.startsWith('##')) {
        return <h3 key={idx} className="text-lg font-semibold mt-4 mb-2 text-foreground">{line.replace(/^#+\s*/, '')}</h3>;
      }
      if (line.startsWith('#')) {
        return <h2 key={idx} className="text-xl font-bold mt-4 mb-2 text-foreground">{line.replace(/^#+\s*/, '')}</h2>;
      }
      if (line.startsWith('- ') || line.startsWith('• ')) {
        return (
          <div key={idx} className="flex items-start gap-2 ml-2 my-1">
            <span className="text-accent mt-1.5">•</span>
            <span className="text-foreground/90">{line.replace(/^[-•]\s*/, '')}</span>
          </div>
        );
      }
      if (line.match(/^\d+\./)) {
        return (
          <div key={idx} className="flex items-start gap-2 ml-2 my-1">
            <span className="text-accent font-medium">{line.match(/^\d+/)[0]}.</span>
            <span className="text-foreground/90">{line.replace(/^\d+\.\s*/, '')}</span>
          </div>
        );
      }
      if (line.startsWith('**') && line.endsWith('**')) {
        return <p key={idx} className="font-semibold my-2 text-foreground">{line.replace(/\*\*/g, '')}</p>;
      }
      if (line.trim() === '') {
        return <div key={idx} className="h-2" />;
      }
      return <p key={idx} className="my-1.5 text-foreground/90 leading-relaxed">{line}</p>;
    });
  };

  return (
    <div data-testid="insights-page">
      <PageHeader
        title="AI Insights"
        subtitle="Powered by GPT-5.2"
        month={month}
        setMonth={setMonth}
        onMenuClick={onMenuClick}
        actions={
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r from-violet-500/10 to-purple-500/10 border border-violet-500/20">
            <Sparkles className="w-4 h-4 text-violet-500" />
            <span className="text-sm font-medium text-violet-600 dark:text-violet-400">AI Powered</span>
          </div>
        }
      />

      <div className="page-content space-y-6">
        {/* Quick Stats */}
        {quickStats && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Total Income"
              value={formatCurrency(quickStats.current_month.income)}
              change={`${quickStats.changes.income_change_pct > 0 ? '+' : ''}${quickStats.changes.income_change_pct}% vs last month`}
              changeType={quickStats.changes.income_change >= 0 ? 'positive' : 'negative'}
              icon={TrendingUp}
              color="bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600"
            />
            <StatCard
              title="Total Expenses"
              value={formatCurrency(quickStats.current_month.expenses)}
              change={`${quickStats.changes.expenses_change_pct > 0 ? '+' : ''}${quickStats.changes.expenses_change_pct}% vs last month`}
              changeType={quickStats.changes.expenses_change <= 0 ? 'positive' : 'negative'}
              icon={Wallet}
              color="bg-rose-100 dark:bg-rose-900/30 text-rose-600"
            />
            <StatCard
              title="Net Savings"
              value={formatCurrency(quickStats.current_month.savings)}
              change={`${quickStats.current_month.savings_rate}% savings rate`}
              changeType={quickStats.current_month.savings >= 0 ? 'positive' : 'negative'}
              icon={PiggyBank}
              color="bg-blue-100 dark:bg-blue-900/30 text-blue-600"
            />
            <StatCard
              title="Transactions"
              value={quickStats.current_month.transaction_count}
              change="This month"
              icon={BarChart3}
              color="bg-violet-100 dark:bg-violet-900/30 text-violet-600"
            />
          </div>
        )}

        {/* Top Categories */}
        {quickStats?.top_categories && quickStats.top_categories.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-violet-500" />
                Top Spending Categories
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {quickStats.top_categories.map((cat, idx) => (
                  <div key={idx} className="flex items-center gap-4">
                    <div 
                      className="w-3 h-3 rounded-full flex-shrink-0" 
                      style={{ backgroundColor: cat.color }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium truncate">{cat.name}</span>
                        <span className="font-semibold">{formatCurrency(cat.amount)}</span>
                      </div>
                      <div className="h-2 bg-secondary rounded-full overflow-hidden">
                        <div 
                          className="h-full rounded-full transition-all duration-500"
                          style={{ 
                            width: `${(cat.amount / quickStats.current_month.expenses) * 100}%`,
                            backgroundColor: cat.color 
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Insight Generator Cards */}
        <div>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5 text-violet-500" />
            Generate AI Insights
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insightTypes.map((insight) => (
              <InsightCard
                key={insight.type}
                title={insight.title}
                icon={insight.icon}
                color={insight.color}
                description={insight.description}
                loading={loadingType === insight.type}
                onClick={() => generateInsight(insight.type)}
              />
            ))}
          </div>
        </div>

        {/* Generated Insight Display */}
        {(activeInsight || insightContent) && (
          <Card className="border-2 border-violet-500/20 bg-gradient-to-br from-violet-500/5 to-purple-500/5">
            <CardHeader className="border-b border-border/50">
              <CardTitle className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-violet-500/10">
                  <Lightbulb className="w-5 h-5 text-violet-500" />
                </div>
                <div>
                  <span className="text-lg">
                    {insightTypes.find(i => i.type === activeInsight)?.title || 'AI Insight'}
                  </span>
                  <p className="text-sm font-normal text-muted-foreground mt-0.5">
                    Generated for {month}
                  </p>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="relative">
                    <div className="w-16 h-16 rounded-full border-4 border-violet-500/20 border-t-violet-500 animate-spin" />
                    <Brain className="w-6 h-6 text-violet-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                  </div>
                  <p className="mt-4 text-muted-foreground">Analyzing your financial data...</p>
                  <p className="text-sm text-muted-foreground/70">This may take a few seconds</p>
                </div>
              ) : insightContent ? (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  {formatInsightContent(insightContent.content)}
                </div>
              ) : null}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
