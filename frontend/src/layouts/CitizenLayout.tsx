import { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, FileWarning, MapPin, Bell, UserCircle, LogOut } from "lucide-react";
import clsx from "clsx";
import { useAuth } from "@/context/AuthContext";
import { resolveUploadUrl } from "@/services/profileService";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, enabled: true },
  { to: "/report-issue", label: "Report Issue", icon: FileWarning, enabled: true },
  { to: "/issues", label: "My Issues", icon: FileWarning, enabled: true },
  { to: "/nearby-issues", label: "Nearby Issues", icon: MapPin, enabled: true },
  { to: "/notifications", label: "Notifications", icon: Bell, enabled: false },
  { to: "/profile", label: "Profile", icon: UserCircle, enabled: true },
];

export function CitizenLayout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen bg-slate-50 flex">
      <aside className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col">
        <div className="px-5 py-5 border-b border-slate-100">
          <div className="inline-flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-brand-500" />
            <span className="text-sm font-semibold tracking-wide text-brand-800 uppercase">CivicPulse</span>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, enabled }) =>
            enabled ? (
              <NavLink key={to} to={to}
                className={({ isActive }) => clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )}>
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ) : (
              <div key={to} title="Coming soon" className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 cursor-not-allowed">
                <Icon className="h-4 w-4" />
                {label}
              </div>
            )
          )}
        </nav>
        <div className="px-3 py-4 border-t border-slate-100">
          <button onClick={logout} className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900">
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-slate-200 bg-white flex items-center justify-end px-6 gap-3">
          <span className="text-sm text-slate-500">{user?.email}</span>
          {user?.profile_image_url ? (
            <img src={resolveUploadUrl(user.profile_image_url)} alt={user.full_name} className="h-8 w-8 rounded-full object-cover border border-slate-200" />
          ) : (
            <div className="h-8 w-8 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-semibold">
              {user?.full_name?.[0]?.toUpperCase()}
            </div>
          )}
        </header>
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}
