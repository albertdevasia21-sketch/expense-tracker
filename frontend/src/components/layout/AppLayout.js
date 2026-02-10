import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Menu } from "lucide-react";

export const AppLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-layout">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <main className="app-main">
        <Outlet context={{ onMenuClick: () => setSidebarOpen(true) }} />
      </main>

      {/* Mobile menu button */}
      <button
        className="mobile-menu-btn"
        onClick={() => setSidebarOpen(true)}
        data-testid="mobile-menu-btn"
      >
        <Menu className="w-6 h-6" />
      </button>
    </div>
  );
};
