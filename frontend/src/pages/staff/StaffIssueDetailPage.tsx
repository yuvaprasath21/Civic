import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { ArrowLeft, Camera, Lock, MapPin } from "lucide-react";

import { StaffLayout } from "@/layouts/StaffLayout";
import { Button } from "@/components/common/Button";
import { ApiError } from "@/api/client";
import { staffService, StaffIssueDetail } from "@/services/staffService";
import { resolveUploadUrl } from "@/services/profileService";
import { CATEGORY_LABELS, PRIORITY_COLORS, STATUS_COLORS, STATUS_LABELS } from "@/utils/issueDisplay";

const IMAGE_GROUPS: { type: string; label: string }[] = [
  { type: "REPORT", label: "Reported by citizen" },
  { type: "BEFORE_WORK", label: "Before work" },
  { type: "AFTER_WORK", label: "After work (evidence)" },
];

function PhotoUpload({ label, onFiles, busy }: { label: string; onFiles: (f: File[]) => void; busy: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <>
      <Button variant="secondary" isLoading={busy} onClick={() => ref.current?.click()}>
        <Camera className="h-4 w-4" />{label}
      </Button>
      <input ref={ref} type="file" multiple accept="image/jpeg,image/png,image/webp" className="hidden"
        onChange={(e) => { const files = Array.from(e.target.files ?? []); if (files.length) onFiles(files); e.target.value = ""; }} />
    </>
  );
}

export default function StaffIssueDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [issue, setIssue] = useState<StaffIssueDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const [noteBody, setNoteBody] = useState("");
  const [noteVisible, setNoteVisible] = useState(false);
  const [percent, setPercent] = useState(0);
  const [progressNote, setProgressNote] = useState("");
  const [resolveNotes, setResolveNotes] = useState("");

  const load = useCallback(() => {
    if (!id) return;
    staffService.getIssue(id)
      .then((d) => { setIssue(d); setPercent(d.progress_percent ?? 0); })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load the issue."))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(load, [load]);

  const run = async (key: string, action: () => Promise<unknown>, success: string) => {
    setBusy(key);
    try {
      await action();
      toast.success(success);
      load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <StaffLayout><div className="max-w-3xl h-64 rounded-xl bg-slate-100 animate-pulse" /></StaffLayout>;
  if (error || !issue || !id) {
    return (
      <StaffLayout>
        <div className="max-w-3xl rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error ?? "Issue not found."}</div>
      </StaffLayout>
    );
  }

  const a = issue.assignment_status;
  const active = a === "PENDING" || a === "ACCEPTED" || a === "IN_PROGRESS";
  const hasAfterPhoto = issue.images.some((i) => i.image_type === "AFTER_WORK");

  return (
    <StaffLayout>
      <div className="max-w-3xl">
        <Link to="/staff/issues" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-4">
          <ArrowLeft className="h-4 w-4" />My assignments
        </Link>

        <div className="flex items-start justify-between gap-4 mb-1">
          <h1 className="text-2xl font-semibold text-slate-900">{issue.title}</h1>
          <span className="text-sm text-slate-400 whitespace-nowrap">{issue.reference_code}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2 mb-5">
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${PRIORITY_COLORS[issue.priority_level]}`}>{issue.priority_level} · {Math.round(issue.priority_score)}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[issue.status]}`}>{STATUS_LABELS[issue.status]}</span>
          <span className="text-xs text-slate-400">{CATEGORY_LABELS[issue.category]}</span>
          {issue.report_count > 1 && <span className="text-xs text-slate-500">{issue.report_count} citizen reports</span>}
        </div>

        {issue.description && <p className="text-sm text-slate-600 mb-4">{issue.description}</p>}
        <p className="flex items-start gap-2 text-sm text-slate-500 mb-8">
          <MapPin className="h-4 w-4 mt-0.5 shrink-0" />
          <span>
            {issue.location.address_text || `${issue.location.latitude.toFixed(5)}, ${issue.location.longitude.toFixed(5)}`}
            {issue.location.city && ` · ${issue.location.city}`}{" "}
            <a className="text-emerald-700 underline" target="_blank" rel="noreferrer"
              href={`https://www.openstreetmap.org/?mlat=${issue.location.latitude}&mlon=${issue.location.longitude}#map=18/${issue.location.latitude}/${issue.location.longitude}`}>
              Open map
            </a>
          </span>
        </p>

        {/* ---- actions ---- */}
        {active && (
          <section className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-5 mb-8 space-y-5">
            <h2 className="text-sm font-semibold text-slate-900">
              {a === "PENDING" && "Step 1 of 3 — accept this assignment"}
              {a === "ACCEPTED" && "Step 2 of 3 — start work when you're on site"}
              {a === "IN_PROGRESS" && "Step 3 of 3 — finish the work and resolve"}
            </h2>

            {a === "PENDING" && (
              <Button isLoading={busy === "accept"} onClick={() => run("accept", () => staffService.accept(id), "Assignment accepted.")}>Accept assignment</Button>
            )}

            {a !== "PENDING" && (
              <div className="flex flex-wrap gap-2">
                <PhotoUpload label="Add 'before' photos" busy={busy === "before"}
                  onFiles={(f) => run("before", () => staffService.uploadPhotos(id, "BEFORE_WORK", f), "Before photos uploaded.")} />
                {a === "ACCEPTED" && (
                  <Button isLoading={busy === "start"} onClick={() => run("start", () => staffService.start(id), "Work started.")}>Start work</Button>
                )}
                {a === "IN_PROGRESS" && (
                  <PhotoUpload label="Add 'after' photos" busy={busy === "after"}
                    onFiles={(f) => run("after", () => staffService.uploadPhotos(id, "AFTER_WORK", f), "After photos uploaded.")} />
                )}
              </div>
            )}

            {a === "IN_PROGRESS" && (
              <div className="space-y-2">
                <label className="block text-sm font-medium text-slate-700">Progress: {percent}%</label>
                <input type="range" min={0} max={99} value={percent} onChange={(e) => setPercent(Number(e.target.value))} className="w-full accent-emerald-600" />
                <input type="text" value={progressNote} onChange={(e) => setProgressNote(e.target.value)} placeholder="What's been done? (shown to the citizen)"
                  className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/40" />
                <Button variant="secondary" isLoading={busy === "progress"}
                  onClick={() => run("progress", () => staffService.updateProgress(id, percent, progressNote.trim() || undefined), "Progress updated.").then(() => setProgressNote(""))}>
                  Update progress
                </Button>
              </div>
            )}

            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">Add a note</label>
              <textarea rows={2} value={noteBody} onChange={(e) => setNoteBody(e.target.value)} placeholder="Site details, materials needed, access instructions…"
                className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/40" />
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <input type="checkbox" checked={noteVisible} onChange={(e) => setNoteVisible(e.target.checked)} className="accent-emerald-600" />
                  Visible to the citizen
                </label>
                <Button variant="secondary" disabled={!noteBody.trim()} isLoading={busy === "note"}
                  onClick={() => run("note", () => staffService.addNote(id, noteBody.trim(), noteVisible), "Note added.").then(() => setNoteBody(""))}>
                  Add note
                </Button>
              </div>
            </div>

            {a === "IN_PROGRESS" && (
              <div className="space-y-2 border-t border-emerald-100 pt-5">
                <label className="block text-sm font-medium text-slate-700">Resolution notes (optional)</label>
                <textarea rows={2} value={resolveNotes} onChange={(e) => setResolveNotes(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/40" />
                <Button isLoading={busy === "resolve"} disabled={!hasAfterPhoto}
                  onClick={() => run("resolve", () => staffService.resolve(id, resolveNotes.trim() || undefined), "Issue marked as resolved.")}>
                  Mark as resolved
                </Button>
                {!hasAfterPhoto && <p className="text-xs text-amber-700">Upload at least one &lsquo;after&rsquo; photo as evidence to enable this.</p>}
              </div>
            )}
          </section>
        )}
        {!active && (
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 mb-8">
            {a === "COMPLETED" ? "You completed this assignment." : "This issue was reassigned to someone else."}
            {issue.staff_notes && <p className="mt-1 text-slate-500">Your notes: {issue.staff_notes}</p>}
          </div>
        )}

        {/* ---- photos ---- */}
        {IMAGE_GROUPS.map(({ type, label }) => {
          const imgs = issue.images.filter((i) => i.image_type === type);
          if (!imgs.length) return null;
          return (
            <div key={type} className="mb-6">
              <h3 className="text-sm font-semibold text-slate-900 mb-2">{label}</h3>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                {imgs.map((img) => (
                  <a key={img.id} href={resolveUploadUrl(img.url)} target="_blank" rel="noreferrer">
                    <img src={resolveUploadUrl(img.url)} alt="" className="aspect-square w-full object-cover rounded-lg border border-slate-200" />
                  </a>
                ))}
              </div>
            </div>
          );
        })}

        {/* ---- timeline ---- */}
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-slate-900 mb-3">Timeline</h2>
          <ol className="space-y-4 border-l-2 border-slate-100 pl-4">
            {issue.status_history.map((e, idx) => (
              <li key={idx} className="relative">
                <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-emerald-500" />
                <p className="text-sm font-medium text-slate-800">{STATUS_LABELS[e.to_status]}</p>
                {e.note && <p className="text-sm text-slate-500">{e.note}</p>}
                <p className="text-xs text-slate-400 mt-0.5">{new Date(e.created_at).toLocaleString()}{e.changed_by_name && ` · ${e.changed_by_name}`}</p>
              </li>
            ))}
          </ol>
        </div>

        {/* ---- notes & comments ---- */}
        <div>
          <h2 className="text-sm font-semibold text-slate-900 mb-3">Notes &amp; comments</h2>
          {issue.comments.length === 0 && <p className="text-sm text-slate-400">Nothing yet.</p>}
          <div className="space-y-3">
            {issue.comments.map((c) => (
              <div key={c.id} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
                <p className="text-sm">
                  <span className="font-medium text-slate-800">{c.author_name}</span>{" "}
                  <span className="text-xs text-slate-400">{new Date(c.created_at).toLocaleString()}</span>
                  {c.is_internal && <span className="ml-2 inline-flex items-center gap-1 text-xs text-amber-700"><Lock className="h-3 w-3" />internal</span>}
                </p>
                <p className="text-sm text-slate-600 mt-0.5">{c.body}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </StaffLayout>
  );
}
