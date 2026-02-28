import type { ReactNode } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Home, Search, GitBranch } from "lucide-react";
import { clsx } from "clsx";

interface NavItem {
  label: string;
  path: string;
  icon: ReactNode;
}

const navItems: NavItem[] = [
  { label: "Saved Searches", path: "/", icon: <Home size={18} /> },
  { label: "New Search", path: "/search/new", icon: <Search size={18} /> },
  { label: "Pipeline", path: "/pipeline", icon: <GitBranch size={18} /> },
];

export function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top nav */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-14">
          <span className="font-bold text-blue-600 text-lg tracking-tight">
            Deal Shortlist
          </span>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  pathname === item.path || (item.path !== "/" && pathname.startsWith(item.path))
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:bg-gray-100"
                )}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        {children}
      </main>
    </div>
  );
}
