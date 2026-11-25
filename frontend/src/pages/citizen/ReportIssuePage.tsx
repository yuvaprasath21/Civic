import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { ImagePlus, Video, X, Sparkles } from "lucide-react";

import { CitizenLayout } from "@/layouts/CitizenLayout";
import { StepIndicator } from "@/components/forms/StepIndicator";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/common/Button";
import { LocationPicker } from "@/components/maps/LocationPicker";
import { issueService } from "@/services/issueService";
import { aiService, AIAnalysisPreview } from "@/services/aiService";
import { ApiError } from "@/api/client";
import { CATEGORY_OPTIONS, SEVERITY_LABELS } from "@/utils/issueDisplay";
import type { IssueCategory, SeverityLevel } from "@/types/domain";

const STEPS = ["Photos", "Category", "Location", "Details", "Review"];
const MAX_IMAGES = 5;
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

interface WizardState {
  images: File[];
  video: File | null;
  category: IssueCategory | null;
  severity: SeverityLevel;
  latitude: number | null;
  longitude: number | null;
  address_text: string;
  landmark: string;
  city: string;
  pincode: string;
  title: string;
  description: string;
}

const initialState: WizardState = {
  images: [], video: null, category: null, severity: "MEDIUM", latitude: null, longitude: null,
  address_text: "", landmark: "", city: "", pincode: "", title: "", description: "",
};

export default function ReportIssuePage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [data, setData] = useState<WizardState>(initialState);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [aiSuggestion, setAiSuggestion] = useState<AIAnalysisPreview | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [categoryTouchedByUser, setCategoryTouchedByUser] = useState(false);

  const imagePreviews = useMemo(() => data.images.map((f) => URL.createObjectURL(f)), [data.images]);

  const patch = (partial: Partial<WizardState>) => setData((prev) => ({ ...prev, ...partial }));

  const canProceed = (): boolean => {
    switch (step) {
      case 1: return data.images.length > 0;
      case 2: return data.category !== null;
      case 3: return data.latitude !== null && data.longitude !== null;
      case 4: return data.title.trim().length >= 5;
      default: return true;
    }
  };

  const goNext = async () => {
    if (step === 1 && data.images.length > 0) {
      setIsAnalyzing(true);
      setAiError(null);
      try {
        const suggestion = await aiService.analyzeImage(data.images[0]);
        setAiSuggestion(suggestion);
        if (!categoryTouchedByUser) {
          patch({ category: suggestion.category, severity: suggestion.severity });
        }
      } catch (err) {
        setAiSuggestion(null);
        setAiError(err instanceof ApiError ? "AI analysis is unavailable right now — you can still select the category manually." : null);
      } finally {
        setIsAnalyzing(false);
      }
    }
    setStep((s) => Math.min(s + 1, STEPS.length + 1));
  };
  const goBack = () => setStep((s) => Math.max(s - 1, 1));

  const onSelectImages = (files: FileList | null) => {
    if (!files) return;
    const incoming = Array.from(files).filter((f) => ALLOWED_IMAGE_TYPES.includes(f.type));
    if (incoming.length !== files.length) toast.error("Only JPEG, PNG, and WebP images are supported.");
    const combined = [...data.images, ...incoming].slice(0, MAX_IMAGES);
    if (data.images.length + incoming.length > MAX_IMAGES) toast.error(`You can upload up to ${MAX_IMAGES} images.`);
    patch({ images: combined });
  };

  const removeImage = (idx: number) => patch({ images: data.images.filter((_, i) => i !== idx) });

  const onSelectVideo = (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    if (!["video/mp4", "video/quicktime"].includes(file.type)) {
      toast.error("Only MP4 and MOV videos are supported.");
      return;
    }
    patch({ video: file });
  };

  const onSubmit = async () => {
    if (!data.category || data.latitude === null || data.longitude === null) return;
    setIsSubmitting(true);
    try {
      const issue = await issueService.createIssue({
        title: data.title.trim(),
        description: data.description.trim() || undefined,
        category: data.category,
        severity: data.severity,
        latitude: data.latitude,
        longitude: data.longitude,
        address_text: data.address_text.trim() || undefined,
        landmark: data.landmark.trim() || undefined,
        city: data.city.trim() || undefined,
        pincode: data.pincode.trim() || undefined,
        images: data.images,
        video: data.video ?? undefined,
      });
      toast.success(`Issue ${issue.reference_code} submitted successfully.`);
      navigate(`/issues/${issue.id}`, { replace: true });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to submit issue. Please try again.");
      setIsSubmitting(false);
    }
  };

  return (
    <CitizenLayout>
      <div className="max-w-2xl">
        <h1 className="text-2xl font-semibold text-slate-900 mb-1">Report a civic issue</h1>
        <p className="text-slate-500 text-sm mb-8">A few quick steps — photos, category, location and details.</p>

        <StepIndicator steps={STEPS} currentStep={Math.min(step, STEPS.length)} />

        <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8">
          {step === 1 && (
            <div>
              <h2 className="text-lg font-medium text-slate-900 mb-1">Add photos</h2>
              <p className="text-sm text-slate-500 mb-5">At least one clear photo of the issue. You can add up to {MAX_IMAGES}.</p>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 mb-4">
                {imagePreviews.map((src, idx) => (
                  <div key={src} className="relative aspect-square rounded-lg overflow-hidden border border-slate-200">
                    <img src={src} alt={`Upload ${idx + 1}`} className="h-full w-full object-cover" />
                    <button type="button" onClick={() => removeImage(idx)} className="absolute top-1 right-1 h-6 w-6 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
                {data.images.length < MAX_IMAGES && (
                  <label className="aspect-square rounded-lg border-2 border-dashed border-slate-300 flex flex-col items-center justify-center gap-1.5 text-slate-400 cursor-pointer hover:border-brand-400 hover:text-brand-500 transition-colors">
                    <ImagePlus className="h-6 w-6" />
                    <span className="text-xs font-medium">Add photo</span>
                    <input type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={(e) => onSelectImages(e.target.files)} />
                  </label>
                )}
              </div>
              <label className="flex items-center gap-2 text-sm text-brand-600 hover:text-brand-700 cursor-pointer w-fit">
                <Video className="h-4 w-4" />
                {data.video ? `Video attached: ${data.video.name}` : "Attach a video (optional)"}
                <input type="file" accept="video/mp4,video/quicktime" className="hidden" onChange={(e) => onSelectVideo(e.target.files)} />
              </label>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-lg font-medium text-slate-900 mb-1">What kind of issue is this?</h2>
              {aiSuggestion && (
                <div className="flex items-start gap-3 rounded-lg bg-brand-50 border border-brand-100 px-4 py-3 mb-5">
                  <Sparkles className="h-4 w-4 mt-0.5 shrink-0 text-brand-600" />
                  <div className="text-sm">
                    <p className="text-brand-900 font-medium">Detected: {CATEGORY_OPTIONS.find((c) => c.value === aiSuggestion.category)?.label}</p>
                    <p className="text-brand-700">Confidence: {Math.round(aiSuggestion.confidence * 100)}% · Severity: {SEVERITY_LABELS[aiSuggestion.severity]}</p>
                    <p className="text-brand-600 text-xs mt-1">Not quite right? Select a different category below — your choice is what gets submitted.</p>
                  </div>
                </div>
              )}
              {aiError && <div className="rounded-lg bg-amber-50 border border-amber-100 px-3.5 py-2.5 text-sm text-amber-800 mb-5">{aiError}</div>}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-6">
                {CATEGORY_OPTIONS.map((opt) => {
                  const isAiPick = aiSuggestion?.category === opt.value;
                  const isSelected = data.category === opt.value;
                  return (
                    <button key={opt.value} type="button"
                      onClick={() => { setCategoryTouchedByUser(true); patch({ category: opt.value }); }}
                      className={`relative rounded-lg border px-3 py-2.5 text-sm font-medium text-left transition-colors ${isSelected ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200 text-slate-600 hover:border-slate-300"}`}>
                      {opt.label}
                      {isAiPick && <Sparkles className={`absolute top-1.5 right-1.5 h-3 w-3 ${isSelected ? "text-brand-500" : "text-slate-300"}`} />}
                    </button>
                  );
                })}
              </div>
              <p className="text-sm font-medium text-slate-700 mb-2">Severity</p>
              <div className="flex gap-2">
                {(Object.keys(SEVERITY_LABELS) as SeverityLevel[]).map((level) => (
                  <button key={level} type="button" onClick={() => patch({ severity: level })}
                    className={`rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors ${data.severity === level ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200 text-slate-600 hover:border-slate-300"}`}>
                    {SEVERITY_LABELS[level]}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 className="text-lg font-medium text-slate-900 mb-1">Where is this happening?</h2>
              <p className="text-sm text-slate-500 mb-4">Pin the exact location on the map.</p>
              <LocationPicker latitude={data.latitude} longitude={data.longitude} onChange={(lat, lng) => patch({ latitude: lat, longitude: lng })} />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5">
                <TextField label="Address / landmark" placeholder="Optional" value={data.address_text} onChange={(e) => patch({ address_text: e.target.value })} />
                <TextField label="City" placeholder="Optional" value={data.city} onChange={(e) => patch({ city: e.target.value })} />
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <h2 className="text-lg font-medium text-slate-900 mb-1">Describe the issue</h2>
              <TextField label="Title" placeholder="e.g. Large pothole outside the school gate" value={data.title} onChange={(e) => patch({ title: e.target.value })} hint="At least 5 characters." />
              <div className="w-full">
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Description</label>
                <textarea rows={5} className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
                  placeholder="Any extra detail that helps the department resolve this faster (optional)." value={data.description} onChange={(e) => patch({ description: e.target.value })} />
              </div>
            </div>
          )}

          {step === 5 && (
            <div>
              <h2 className="text-lg font-medium text-slate-900 mb-4">Review your report</h2>
              <div className="grid grid-cols-4 gap-2 mb-5">
                {imagePreviews.map((src) => <img key={src} src={src} className="aspect-square rounded-lg object-cover border border-slate-200" />)}
              </div>
              <dl className="divide-y divide-slate-100 text-sm">
                {[
                  ["Category", CATEGORY_OPTIONS.find((c) => c.value === data.category)?.label],
                  ["Severity", SEVERITY_LABELS[data.severity]],
                  ["Location", `${data.latitude?.toFixed(5)}, ${data.longitude?.toFixed(5)}`],
                  ["City", data.city || "—"],
                  ["Title", data.title],
                  ["Description", data.description || "—"],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between py-2.5 gap-4">
                    <dt className="text-slate-500">{label}</dt>
                    <dd className="text-slate-900 font-medium text-right">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>

        <div className="flex justify-between mt-6">
          <Button variant="secondary" onClick={goBack} disabled={step === 1 || isSubmitting}>Back</Button>
          {step < STEPS.length ? (
            <Button onClick={goNext} disabled={!canProceed() || isAnalyzing} isLoading={isAnalyzing}>
              {isAnalyzing ? "Analyzing photo..." : "Continue"}
            </Button>
          ) : (
            <Button onClick={onSubmit} isLoading={isSubmitting}>{isSubmitting ? "Submitting..." : "Submit report"}</Button>
          )}
        </div>
      </div>
    </CitizenLayout>
  );
}
