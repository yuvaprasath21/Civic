import { forwardRef, InputHTMLAttributes } from "react";
import clsx from "clsx";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  ({ label, error, hint, id, className, ...rest }, ref) => {
    const fieldId = id ?? rest.name;
    return (
      <div className="w-full">
        <label htmlFor={fieldId} className="block text-sm font-medium text-slate-700 mb-1.5">
          {label}
        </label>
        <input
          ref={ref}
          id={fieldId}
          className={clsx(
            "w-full rounded-lg border px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400",
            "focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500",
            "transition-colors",
            error ? "border-red-400 bg-red-50/40" : "border-slate-300 bg-white",
            className
          )}
          aria-invalid={!!error}
          aria-describedby={error ? `${fieldId}-error` : undefined}
          {...rest}
        />
        {error ? (
          <p id={`${fieldId}-error`} className="mt-1.5 text-sm text-red-600">{error}</p>
        ) : hint ? (
          <p className="mt-1.5 text-sm text-slate-400">{hint}</p>
        ) : null}
      </div>
    );
  }
);
TextField.displayName = "TextField";
