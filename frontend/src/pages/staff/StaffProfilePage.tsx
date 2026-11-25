import { useEffect, useState } from "react";
import { StaffLayout } from "@/layouts/StaffLayout";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/api/client";
import { staffService, StaffStats } from "@/services/staffService";

export default function StaffProfilePage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<StaffStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    staffService.stats().then(setStats).catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load profile."));
  }, []);

  const rows: [string, string | number | undefined][] = [
    ["Name", user?.full_name],
    ["Email", user?.email],
    ["Employee code", stats?.employee_code],
    ["Designation", stats?.designation ?? "—"],
    ["Department", stats?.department_name ?? "—"],
    ["Current workload", stats?.current_workload],
    ["Issues resolved", stats?.total_resolved],
    ["Average resolution time", stats?.average_resolution_hours != null ? `${stats.average_resolution_hours.toFixed(1)} hours` : "—"],
  ];

  return (
    <StaffLayout>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Profile</h1>
      <p className="text-slate-500 text-sm mb-8">Your details and work statistics. Contact your department admin to change them.</p>
      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 mb-6 max-w-xl">{error}</div>}
      <dl className="max-w-xl divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between px-5 py-3">
            <dt className="text-slate-500">{label}</dt>
            <dd className="font-medium text-slate-900">{value ?? <span className="inline-block h-4 w-16 rounded bg-slate-100 animate-pulse" />}</dd>
          </div>
        ))}
      </dl>
    </StaffLayout>
  );
}
