import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useLocation, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { AuthLayout } from "@/layouts/AuthLayout";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/common/Button";
import { useAuth, ApiError } from "@/context/AuthContext";
import { roleHomePath } from "@/routes/roleHomePath";

const schema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    try {
      const user = await login(values);
      toast.success(`Welcome back, ${user.full_name.split(" ")[0]}`);
      const redirectTo = (location.state as { from?: string } | null)?.from;
      navigate(redirectTo ?? roleHomePath(user.role), { replace: true });
    } catch (err) {
      setError("root", { message: err instanceof ApiError ? err.message : "Something went wrong. Please try again." });
    }
  };

  return (
    <AuthLayout title="Sign in" subtitle="Track civic issues you've reported and their resolution status."
      footer={<>Don&apos;t have an account? <Link to="/register" className="text-brand-600 font-medium hover:text-brand-700">Create one</Link></>}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {errors.root && <div className="rounded-lg bg-red-50 border border-red-200 px-3.5 py-2.5 text-sm text-red-700">{errors.root.message}</div>}
        <TextField label="Email address" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
        <TextField label="Password" type="password" autoComplete="current-password" error={errors.password?.message} {...register("password")} />
        <div className="flex justify-end">
          <Link to="/forgot-password" className="text-sm text-brand-600 hover:text-brand-700">Forgot password?</Link>
        </div>
        <Button type="submit" isLoading={isSubmitting} className="w-full">Sign in</Button>
      </form>
    </AuthLayout>
  );
}
