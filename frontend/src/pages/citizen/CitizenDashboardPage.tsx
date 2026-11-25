import { CitizenLayout } from "@/layouts/CitizenLayout";
import { useAuth } from "@/context/AuthContext";

export default function CitizenDashboardPage() {
  const { user } = useAuth();
  return (
    <CitizenLayout>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Welcome, {user?.full_name.split(" ")[0]}</h1>
      <p className="text-slate-500 text-sm mb-8">Report an issue, track its status, and see your impact.</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Reports submitted", value: "—" },
          { label: "Open issues", value: "—" },
          { label: "Resolved issues", value: "—" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border border-slate-200 bg-white p-5">
            <p className="text-sm text-slate-500">{stat.label}</p>
            <p className="text-2xl font-semibold text-slate-900 mt-1">{stat.value}</p>
          </div>
        ))}
      </div>
    </CitizenLayout>
  );
}
