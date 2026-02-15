import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount, currency = "CAD") {
  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(dateString) {
  // Parse date string as local time to avoid timezone shift
  // Date strings like "2025-02-14" are interpreted as UTC by default
  // Adding T00:00:00 forces local time interpretation
  const date = new Date(dateString + "T00:00:00");
  return new Intl.DateTimeFormat("en-CA", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function formatShortDate(dateString) {
  // Parse date string as local time to avoid timezone shift
  const date = new Date(dateString + "T00:00:00");
  return new Intl.DateTimeFormat("en-CA", {
    month: "short",
    day: "numeric",
  }).format(date);
}

export function getCurrentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function getMonthName(monthString) {
  const [year, month] = monthString.split("-");
  const date = new Date(parseInt(year), parseInt(month) - 1, 1);
  return new Intl.DateTimeFormat("en-CA", {
    month: "long",
    year: "numeric",
  }).format(date);
}

export function getPreviousMonth(monthString) {
  const [year, month] = monthString.split("-").map(Number);
  const date = new Date(year, month - 2, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

export function getNextMonth(monthString) {
  const [year, month] = monthString.split("-").map(Number);
  const date = new Date(year, month, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

export function getTransactionTypeColor(type) {
  switch (type) {
    case "income":
      return "text-emerald-600 dark:text-emerald-400";
    case "expense":
      return "text-slate-900 dark:text-slate-100";
    case "transfer":
      return "text-blue-600 dark:text-blue-400";
    default:
      return "";
  }
}

export function getMemberColor(memberName) {
  if (memberName?.toLowerCase() === "me") {
    return { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-400" };
  }
  if (memberName?.toLowerCase() === "wife") {
    return { bg: "bg-pink-100 dark:bg-pink-900/30", text: "text-pink-700 dark:text-pink-400" };
  }
  return { bg: "bg-slate-100 dark:bg-slate-800", text: "text-slate-700 dark:text-slate-300" };
}

export function getAccountIcon(type) {
  switch (type) {
    case "checking":
      return "Building2";
    case "savings":
      return "PiggyBank";
    case "credit":
      return "CreditCard";
    case "cash":
      return "Wallet";
    case "loan":
      return "Landmark";
    default:
      return "Banknote";
  }
}

export function getCategoryIcon(groupName) {
  const icons = {
    "Housing": "Home",
    "Transportation": "Car",
    "Utilities": "Zap",
    "Insurance": "Shield",
    "Subscriptions": "Tv",
    "Food": "UtensilsCrossed",
    "Shopping": "ShoppingBag",
    "Health": "Heart",
    "Entertainment": "Film",
    "Travel": "Plane",
    "Gifts & Donations": "Gift",
    "Other": "MoreHorizontal",
    "Income": "TrendingUp",
  };
  return icons[groupName] || "Circle";
}

export function groupBy(array, key) {
  return array.reduce((result, item) => {
    const keyValue = typeof key === "function" ? key(item) : item[key];
    (result[keyValue] = result[keyValue] || []).push(item);
    return result;
  }, {});
}
