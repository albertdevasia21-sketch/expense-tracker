import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
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
  const [subcategories, setSubcategories] = useState([]);
  const [members, setMembers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [tags, setTags] = useState([]);
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const autopostProcessed = useRef(false);

  // Process auto-post recurring transactions on app load
  const processAutopostRecurring = useCallback(async () => {
    if (!isAuthenticated || autopostProcessed.current) return;
    
    try {
      const response = await api.post("/recurring/process-autopost");
      if (response.data.posted_transactions > 0) {
        console.log(`Auto-posted ${response.data.posted_transactions} recurring transaction(s)`);
      }
      autopostProcessed.current = true;
    } catch (error) {
      console.error("Failed to process autopost recurring:", error);
    }
  }, [api, isAuthenticated]);

  const fetchAll = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setLoading(true);
    try {
      // Process auto-post recurring transactions first
      await processAutopostRecurring();
      
      const [catRes, subcatRes, memRes, accRes, merRes, tagRes, goalRes] = await Promise.all([
        api.get("/categories"),
        api.get("/subcategories"),
        api.get("/household-members"),
        api.get("/accounts"),
        api.get("/merchants"),
        api.get("/tags"),
        api.get("/goals"),
      ]);
      
      setCategories(catRes.data);
      setSubcategories(subcatRes.data);
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
  }, [api, isAuthenticated, processAutopostRecurring]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);
  
  // Reset autopost flag when user logs out
  useEffect(() => {
    if (!isAuthenticated) {
      autopostProcessed.current = false;
    }
  }, [isAuthenticated]);

  const getCategoryById = (id) => categories.find((c) => c.id === id);
  const getSubcategoryById = (id) => subcategories.find((s) => s.id === id);
  const getMemberById = (id) => members.find((m) => m.id === id);
  const getAccountById = (id) => accounts.find((a) => a.id === id);
  const getMerchantById = (id) => merchants.find((m) => m.id === id);
  const getDefaultMember = () => members.find((m) => m.is_default) || members[0];
  
  const getSubcategoriesForCategory = (categoryId) => 
    subcategories.filter((s) => s.category_id === categoryId);

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
        subcategories,
        members,
        accounts,
        merchants,
        tags,
        goals,
        loading,
        fetchAll,
        getCategoryById,
        getSubcategoryById,
        getMemberById,
        getAccountById,
        getMerchantById,
        getDefaultMember,
        getSubcategoriesForCategory,
        categoryGroups,
        expenseCategories,
        incomeCategories,
        fixedCategories,
        flexibleCategories,
        setCategories,
        setSubcategories,
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
