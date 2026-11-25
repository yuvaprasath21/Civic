import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";
import { CitizenLayout } from "@/layouts/CitizenLayout";
import { IssueCard } from "@/components/issues/IssueCard";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/common/Button";
import { issueService, IssueSummary } from "@/services/issueService";
import { ApiError } from "@/api/client";

export default function NearbyIssuesPage() {
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [issues, setIssues] = useState<IssueSummary[]>([]);
  const [isLocating, setIsLocating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestLocation = () => {
    if (!navigator.geolocation) { setError("Your browser doesn't support geolocation."); return; }
    setIsLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => { setCoords({ lat: position.coords.latitude, lng: position.coords.longitude }); setIsLocating(false); },
      () => { setError("Couldn't get your location. Please allow location access and try again."); setIsLocating(false); },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  useEffect(() => { requestLocation(); }, []);

  useEffect(() => {
    if (!coords) return;
    setIsLoading(true);
    issueService.listNearby(coords.lat, coords.lng, 3)
      .then((result) => setIssues(result.items))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load nearby issues."))
      .finally(() => setIsLoading(false));
  }, [coords]);

  return (
    <CitizenLayout>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Nearby issues</h1>
      <p className="text-slate-500 text-sm mb-6">Civic issues reported within 3km of your current location.</p>

      {!coords && !isLocating && (
        <EmptyState icon={<MapPin className="h-10 w-10" />} title="Location access needed"
          description="Allow location access to see issues reported near you." action={<Button onClick={requestLocation}>Enable location</Button>} />
      )}
      {isLocating && <p className="text-sm text-slate-400">Getting your location...</p>}
      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 mb-4">{error}</div>}
      {isLoading && (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-24 rounded-xl bg-slate-100 animate-pulse" />)}</div>
      )}
      {!isLoading && coords && issues.length === 0 && !error && (
        <EmptyState icon={<MapPin className="h-10 w-10" />} title="No issues nearby" description="Nothing reported within 3km yet." />
      )}
      {!isLoading && issues.length > 0 && (
        <div className="space-y-3">{issues.map((issue) => <IssueCard key={issue.id} issue={issue} />)}</div>
      )}
    </CitizenLayout>
  );
}
