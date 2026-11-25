import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { CheckCircle2 } from "lucide-react";
import { AuthLayout } from "@/layouts/AuthLayout";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/common/Button";
import { otpService } from "@/services/otpService";
import { ApiError } from "@/api/client";

type Step = "enter" | "verify";

export default function VerifyContactPage() {
  const [step, setStep] = useState<Step>("enter");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [emailOtp, setEmailOtp] = useState("");
  const [mobileOtp, setMobileOtp] = useState("");
  const [emailVerified, setEmailVerified] = useState(false);
  const [mobileVerified, setMobileVerified] = useState(false);
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const errorMessage = (err: unknown) => (err instanceof ApiError ? err.message : "Something went wrong. Please try again.");

  const sendCodes = async (isResend = false) => {
    setBusy(true);
    try {
      const payload = { email: email.trim() || undefined, mobile: mobile.trim() || undefined };
      await (isResend ? otpService.resend(payload) : otpService.send(payload));
      toast.success("Verification codes sent.");
      setStep("verify");
      setCooldown(60);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const verify = async (kind: "email" | "mobile") => {
    setBusy(true);
    try {
      if (kind === "email") {
        await otpService.verifyEmail(email.trim(), emailOtp.trim());
        setEmailVerified(true);
      } else {
        await otpService.verifyMobile(mobile.trim().replace(/[\s-]/g, ""), mobileOtp.trim());
        setMobileVerified(true);
      }
      toast.success(kind === "email" ? "Email verified." : "Mobile number verified.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const wantsEmail = email.trim().length > 0;
  const wantsMobile = mobile.trim().length > 0;
  const allDone = (!wantsEmail || emailVerified) && (!wantsMobile || mobileVerified);

  if (step === "enter") {
    return (
      <AuthLayout title="Verify your contact details" subtitle="We'll send a separate 6-digit code to your email and your mobile number."
        footer={<Link to="/login" className="text-brand-600 font-medium hover:text-brand-700">Back to sign in</Link>}>
        <div className="space-y-4">
          <TextField label="Email address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <TextField label="Mobile number" type="tel" placeholder="+919876543210" value={mobile}
            onChange={(e) => setMobile(e.target.value)} hint="Include the country code, e.g. +91 for India." />
          <Button className="w-full" isLoading={busy} disabled={!wantsEmail && !wantsMobile} onClick={() => sendCodes(false)}>
            Send codes
          </Button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Enter your codes" subtitle="Codes expire in 5 minutes. You have 5 attempts per code.">
      <div className="space-y-6">
        {wantsEmail && (
          <div className="space-y-2">
            <TextField label={`Code sent to ${email}`} inputMode="numeric" maxLength={6} value={emailOtp}
              disabled={emailVerified} onChange={(e) => setEmailOtp(e.target.value.replace(/\D/g, ""))} />
            {emailVerified ? (
              <p className="flex items-center gap-1.5 text-sm text-emerald-600"><CheckCircle2 className="h-4 w-4" />Email verified</p>
            ) : (
              <Button variant="secondary" isLoading={busy} disabled={emailOtp.length < 6} onClick={() => verify("email")}>Verify email</Button>
            )}
          </div>
        )}
        {wantsMobile && (
          <div className="space-y-2">
            <TextField label={`Code sent to ${mobile}`} inputMode="numeric" maxLength={6} value={mobileOtp}
              disabled={mobileVerified} onChange={(e) => setMobileOtp(e.target.value.replace(/\D/g, ""))} />
            {mobileVerified ? (
              <p className="flex items-center gap-1.5 text-sm text-emerald-600"><CheckCircle2 className="h-4 w-4" />Mobile number verified</p>
            ) : (
              <Button variant="secondary" isLoading={busy} disabled={mobileOtp.length < 6} onClick={() => verify("mobile")}>Verify mobile</Button>
            )}
          </div>
        )}

        {allDone ? (
          <Link to="/dashboard"><Button className="w-full">Continue</Button></Link>
        ) : (
          <button type="button" disabled={cooldown > 0 || busy} onClick={() => sendCodes(true)}
            className="text-sm text-brand-600 hover:text-brand-700 disabled:text-slate-400">
            {cooldown > 0 ? `Resend codes in ${cooldown}s` : "Resend codes"}
          </button>
        )}
      </div>
    </AuthLayout>
  );
}
