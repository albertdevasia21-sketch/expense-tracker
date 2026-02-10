import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useAuth } from "./AuthContext";

const DataContext = createContext(null);

export const useData = () => {
  const context = useContext(DataContext);
  if (!context) {
    throw new Error("useData must be used within a DataProvider");
  }
  return context;
};

export const DataProvider = ({ children }) => {
  const { api, isAuthenticated } = useAuth();
  
  const [categories, setCategories] = useState([]);
  const [members, setMembers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [tags, setTags] = useState([]);
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setLoading(true);
    try {
      const [catRes, memRes, accRes, merRes, tagRes, goalRes] = await Promise.all([
        api.get("/categories"),
        api.get("/household-members"),
        api.get("/accounts"),
        api.get("/merchants"),
        api.get("/tags"),
        api.get("/goals"),
      ]);
      
      setCategories(catRes.data);
      setMembers(memRes.data);
      setAccounts(accRes.data);
      setMerchants(merRes.data);
      setTags(tagRes.data);
      setGoals(goalRes.data);
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  }, [api, isAuthenticated]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const getCategoryById = (id) => categories.find((c) => c.id === id);
  const getMemberById = (id) => members.find((m) => m.id === id);
  const getAccountById = (id) => accounts.find((a) => a.id === id);
  const getMerchantById = (id) => merchants.find((m) => m.id === id);
  const getDefaultMember = () => members.find((m) => m.is_default) || members[0];

  const categoryGroups = categories.reduce((acc, cat) => {
    if (!acc[cat.group_name]) {
      acc[cat.group_name] = [];
    }
    acc[cat.group_name].push(cat);
    return acc;
  }, {});

  const expenseCategories = categories.filter((c) => c.type === "expense");
  const incomeCategories = categories.filter((c) => c.type === "income");
  const fixedCategories = categories.filter((c) => c.is_fixed);
  const flexibleCategories = categories.filter((c) => !c.is_fixed && c.type === "expense");

  return (
    <DataContext.Provider
      value={{
        categories,
        members,
        accounts,
        merchants,
        tags,
        goals,
        loading,
        fetchAll,
        getCategoryById,
        getMemberById,
        getAccountById,
        getMerchantById,
        getDefaultMember,
        categoryGroups,
        expenseCategories,
        incomeCategories,
        fixedCategories,
        flexibleCategories,
        setCategories,
        setMembers,
        setAccounts,
        setMerchants,
        setTags,
        setGoals,
      }}
    >
      {children}
    </DataContext.Provider>
  );
};
