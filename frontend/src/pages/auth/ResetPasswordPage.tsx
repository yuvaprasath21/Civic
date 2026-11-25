import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { AuthLayout } from "@/layouts/AuthLayout";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/common/Button";
import { authService } from "@/services/authService";
import { ApiError } from "@/api/client";

const schema = z.object({
  new_password: z.string().min(8, "Password must be at least 8 characters")
    .regex(/[a-zA-Z]/, "Password must contain a letter")
    .regex(/[0-9]/, "Password must contain a digit"),
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
});
type FormValues = z.infer<typeof schema>;

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    if (!token) {
      setError("root", { message: "Reset link is missing or invalid." });
      return;
    }
    try {
      await authService.resetPassword(token, values.new_password);
      toast.success("Password reset. Please sign in.");
      navigate("/login", { replace: true });
    } catch (err) {
      setError("root", { message: err instanceof ApiError ? err.message : "Something went wrong. Please try again." });
    }
  };

  return (
    <AuthLayout title="Reset your password" subtitle="Choose a new password for your account."
      footer={<Link to="/login" className="text-brand-600 font-medium hover:text-brand-700">Back to sign in</Link>}>
      {!token && (
        <div className="mb-4 rounded-lg bg-amber-50 border border-amber-200 px-3.5 py-2.5 text-sm text-amber-800">
          This reset link looks invalid. Request a new one from the{" "}
          <Link to="/forgot-password" className="underline">forgot password</Link> page.
        </div>
      )}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {errors.root && <div className="rounded-lg bg-red-50 border border-red-200 px-3.5 py-2.5 text-sm text-red-700">{errors.root.message}</div>}
        <TextField label="New password" type="password" autoComplete="new-password" error={errors.new_password?.message} {...register("new_password")} />
        <TextField label="Confirm new password" type="password" autoComplete="new-password" error={errors.confirm_password?.message} {...register("confirm_password")} />
        <Button type="submit" isLoading={isSubmitting} className="w-full">Reset password</Button>
      </form>
    </AuthLayout>
  );
}
