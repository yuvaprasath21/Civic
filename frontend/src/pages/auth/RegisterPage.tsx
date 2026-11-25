import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { AuthLayout } from "@/layouts/AuthLayout";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/common/Button";
import { useAuth, ApiError } from "@/context/AuthContext";
import { roleHomePath } from "@/routes/roleHomePath";

const schema = z.object({
  full_name: z.string().min(2, "Enter your full name"),
  email: z.string().email("Enter a valid email address"),
  phone_number: z.string().optional(),
  password: z.string().min(8, "Password must be at least 8 characters")
    .regex(/[a-zA-Z]/, "Password must contain a letter")
    .regex(/[0-9]/, "Password must contain a digit"),
});
type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    try {
      const user = await registerUser({ ...values, phone_number: values.phone_number || undefined });
      toast.success("Account created. Welcome to CivicPulse!");
      navigate(roleHomePath(user.role), { replace: true });
    } catch (err) {
      setError("root", { message: err instanceof ApiError ? err.message : "Something went wrong. Please try again." });
    }
  };

  return (
    <AuthLayout title="Create your account" subtitle="Report civic issues in your area and track their resolution."
      footer={<>Already have an account? <Link to="/login" className="text-brand-600 font-medium hover:text-brand-700">Sign in</Link></>}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {errors.root && <div className="rounded-lg bg-red-50 border border-red-200 px-3.5 py-2.5 text-sm text-red-700">{errors.root.message}</div>}
        <TextField label="Full name" autoComplete="name" error={errors.full_name?.message} {...register("full_name")} />
        <TextField label="Email address" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
        <TextField label="Phone number" type="tel" autoComplete="tel" hint="Optional — used for SMS updates on your reports." error={errors.phone_number?.message} {...register("phone_number")} />
        <TextField label="Password" type="password" autoComplete="new-password" hint="At least 8 characters, with a letter and a number." error={errors.password?.message} {...register("password")} />
        <Button type="submit" isLoading={isSubmitting} className="w-full">Create account</Button>
      </form>
    </AuthLayout>
  );
}
