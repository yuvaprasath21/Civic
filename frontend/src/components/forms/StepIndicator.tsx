import { Check } from "lucide-react";
import clsx from "clsx";

export function StepIndicator({ steps, currentStep }: { steps: string[]; currentStep: number }) {
  return (
    <ol className="flex items-center w-full mb-8">
      {steps.map((label, idx) => {
        const stepNumber = idx + 1;
        const isComplete = stepNumber < currentStep;
        const isCurrent = stepNumber === currentStep;
        return (
          <li key={label} className={clsx("flex items-center", idx !== steps.length - 1 && "flex-1")}>
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={clsx(
                  "h-8 w-8 rounded-full flex items-center justify-center text-xs font-semibold shrink-0",
                  isComplete && "bg-brand-600 text-white",
                  isCurrent && !isComplete && "bg-brand-600 text-white ring-4 ring-brand-100",
                  !isComplete && !isCurrent && "bg-slate-100 text-slate-400"
                )}
              >
                {isComplete ? <Check className="h-4 w-4" /> : stepNumber}
              </div>
              <span className={clsx("text-xs font-medium whitespace-nowrap hidden sm:block", isCurrent ? "text-slate-900" : "text-slate-400")}>
                {label}
              </span>
            </div>
            {idx !== steps.length - 1 && (
              <div className={clsx("h-0.5 flex-1 mx-2 sm:mx-3", isComplete ? "bg-brand-600" : "bg-slate-200")} />
            )}
          </li>
        );
      })}
    </ol>
  );
}
