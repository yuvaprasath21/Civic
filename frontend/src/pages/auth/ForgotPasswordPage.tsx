import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { AuthLayout } from "@/layouts/AuthLayout";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/common/Button";
import { authService } from "@/services/authService";
import { ApiError } from "@/api/client";

const schema = z.object({ email: z.string().email("Enter a valid email address") });
type FormValues = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null);
  const [devResetToken, setDevResetToken] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    try {
      const result = await authService.forgotPassword(values.email);
      setSubmittedMessage(result.message);
      setDevResetToken(result.dev_reset_token ?? null);
    } catch (err) {
      setError("root", { message: err instanceof ApiError ? err.message : "Something went wrong. Please try again." });
    }
  };

  if (submittedMessage) {
    return (
      <AuthLayout title="Check your email">
        <div className="flex flex-col items-center text-center gap-3 py-2">
          <CheckCircle2 className="h-10 w-10 text-brand-600" />
          <p className="text-sm text-slate-600">{submittedMessage}</p>
          {devResetToken && (
            <div className="mt-4 w-full rounded-lg border border-amber-200 bg-amber-50 p-3 text-left">
              <p className="text-xs font-medium text-amber-800 mb-1">Development mode — no email provider configured</p>
              <Link to={`/reset-password?token=${encodeURIComponent(devResetToken)}`} className="text-xs text-brand-700 underline break-all">
                Reset link (dev only)
              </Link>
            </div>
          )}
          <Link to="/login" className="mt-3 text-sm text-brand-600 hover:text-brand-700">Back to sign in</Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Forgot your password?" subtitle="Enter your email and we'll send you a link to reset it."
      footer={<Link to="/login" className="text-brand-600 font-medium hover:text-brand-700">Back to sign in</Link>}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {errors.root && <div className="rounded-lg bg-red-50 border border-red-200 px-3.5 py-2.5 text-sm text-red-700">{errors.root.message}</div>}
        <TextField label="Email address" type="email" error={errors.email?.message} {...register("email")} />
        <Button type="submit" isLoading={isSubmitting} className="w-full">Send reset link</Button>
      </form>
    </AuthLayout>
  );
}
