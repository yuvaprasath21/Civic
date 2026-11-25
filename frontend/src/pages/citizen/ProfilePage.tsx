import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";
import { Camera, Loader2 } from "lucide-react";
import { CitizenLayout } from "@/layouts/CitizenLayout";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/common/Button";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/api/client";
import { CitizenProfile, profileService, resolveUploadUrl } from "@/services/profileService";

const schema = z.object({
  full_name: z.string().min(2, "Enter your full name"),
  phone_number: z.string().optional(),
  address_line: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  pincode: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

function ProfileSkeleton() {
  return (
    <div className="max-w-2xl space-y-6 animate-pulse">
      <div className="h-24 w-24 rounded-full bg-slate-200" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-10 rounded-lg bg-slate-200" />)}
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const { updateUser } = useAuth();
  const [profile, setProfile] = useState<CitizenProfile | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting, isDirty } } = useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    profileService.getMyProfile()
      .then((data) => {
        setProfile(data);
        reset({
          full_name: data.full_name, phone_number: data.phone_number ?? "", address_line: data.address_line ?? "",
          city: data.city ?? "", state: data.state ?? "", pincode: data.pincode ?? "",
        });
      })
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Failed to load profile."))
      .finally(() => setIsLoadingProfile(false));
  }, [reset]);

  const onSubmit = async (values: FormValues) => {
    try {
      const updated = await profileService.updateMyProfile(values);
      setProfile(updated);
      updateUser({ full_name: updated.full_name });
      reset(values);
      toast.success("Profile updated.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to update profile.");
    }
  };

  const onImageSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploadingImage(true);
    try {
      const { profile_image_url } = await profileService.uploadProfileImage(file);
      setProfile((prev) => (prev ? { ...prev, profile_image_url } : prev));
      updateUser({ profile_image_url });
      toast.success("Profile photo updated.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to upload image.");
    } finally {
      setIsUploadingImage(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <CitizenLayout>
      <div className="max-w-2xl">
        <h1 className="text-2xl font-semibold text-slate-900 mb-1">Profile</h1>
        <p className="text-slate-500 text-sm mb-8">Manage your personal details and the address used to pre-fill issue reports.</p>

        {isLoadingProfile && <ProfileSkeleton />}
        {!isLoadingProfile && loadError && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{loadError}</div>
        )}

        {!isLoadingProfile && profile && (
          <div className="space-y-8">
            <div className="flex items-center gap-5">
              <div className="relative">
                {profile.profile_image_url ? (
                  <img src={resolveUploadUrl(profile.profile_image_url)} alt={profile.full_name} className="h-20 w-20 rounded-full object-cover border border-slate-200" />
                ) : (
                  <div className="h-20 w-20 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-2xl font-semibold">
                    {profile.full_name[0]?.toUpperCase()}
                  </div>
                )}
                <button type="button" onClick={() => fileInputRef.current?.click()} disabled={isUploadingImage}
                  className="absolute -bottom-1 -right-1 h-7 w-7 rounded-full bg-brand-600 text-white flex items-center justify-center border-2 border-white hover:bg-brand-700 disabled:opacity-60"
                  aria-label="Change profile photo">
                  {isUploadingImage ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Camera className="h-3.5 w-3.5" />}
                </button>
                <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={onImageSelected} />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">{profile.full_name}</p>
                <p className="text-sm text-slate-500">{profile.email}</p>
                <p className="text-xs text-slate-400 mt-1">{profile.total_reports_submitted} reports submitted</p>
              </div>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <TextField label="Full name" error={errors.full_name?.message} {...register("full_name")} />
                <TextField label="Phone number" type="tel" {...register("phone_number")} />
              </div>
              <TextField label="Address" {...register("address_line")} />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <TextField label="City" {...register("city")} />
                <TextField label="State" {...register("state")} />
                <TextField label="PIN code" {...register("pincode")} />
              </div>
              <div className="flex justify-end pt-2">
                <Button type="submit" isLoading={isSubmitting} disabled={!isDirty}>Save changes</Button>
              </div>
            </form>
          </div>
        )}
      </div>
    </CitizenLayout>
  );
}
