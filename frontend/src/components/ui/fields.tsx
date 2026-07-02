/* Form primitives: Input, PasswordInput, Select, Textarea — one consistent
 * look, every control labelled (WCAG 3.3.2). */
import { forwardRef, useId, useState, type InputHTMLAttributes,
  type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import { cx } from "@/lib/format";

const CONTROL =
  "w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 " +
  "placeholder:text-slate-400 focus:border-brand-500 " +
  "disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500 " +
  "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 " +
  "dark:placeholder:text-slate-500 dark:disabled:bg-slate-800";

interface FieldWrapperProps {
  label?: string;
  hint?: string;
  error?: string;
  id: string;
  children: ReactNode;
}

function FieldWrapper({ label, hint, error, id, children }: FieldWrapperProps) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-300">
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p className="text-xs text-red-600 dark:text-red-400" role="alert">{error}</p>
      ) : hint ? (
        <p className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>
      ) : null}
    </div>
  );
}

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, hint, error, className, id, ...rest }, ref) => {
    const autoId = useId();
    const fieldId = id ?? autoId;
    return (
      <FieldWrapper label={label} hint={hint} error={error} id={fieldId}>
        <input ref={ref} id={fieldId}
               className={cx(CONTROL, "h-10", error && "border-red-400", className)}
               aria-invalid={error ? true : undefined} {...rest} />
      </FieldWrapper>
    );
  },
);
Input.displayName = "Input";

export const PasswordInput = forwardRef<HTMLInputElement, InputProps>(
  ({ label, hint, error, className, id, ...rest }, ref) => {
    const autoId = useId();
    const fieldId = id ?? autoId;
    const [visible, setVisible] = useState(false);
    return (
      <FieldWrapper label={label} hint={hint} error={error} id={fieldId}>
        <div className="relative">
          <input ref={ref} id={fieldId} type={visible ? "text" : "password"}
                 className={cx(CONTROL, "h-10 pr-10", error && "border-red-400", className)}
                 aria-invalid={error ? true : undefined} {...rest} />
          <button type="button" onClick={() => setVisible((v) => !v)}
                  aria-label={visible ? "Fshih fjalëkalimin" : "Shfaq fjalëkalimin"}
                  className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
            {visible ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
          </button>
        </div>
      </FieldWrapper>
    );
  },
);
PasswordInput.displayName = "PasswordInput";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, hint, error, className, id, children, ...rest }, ref) => {
    const autoId = useId();
    const fieldId = id ?? autoId;
    return (
      <FieldWrapper label={label} hint={hint} error={error} id={fieldId}>
        <select ref={ref} id={fieldId}
                className={cx(CONTROL, "h-10 pr-8", error && "border-red-400", className)}
                aria-invalid={error ? true : undefined} {...rest}>
          {children}
        </select>
      </FieldWrapper>
    );
  },
);
Select.displayName = "Select";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, hint, error, className, id, ...rest }, ref) => {
    const autoId = useId();
    const fieldId = id ?? autoId;
    return (
      <FieldWrapper label={label} hint={hint} error={error} id={fieldId}>
        <textarea ref={ref} id={fieldId}
                  className={cx(CONTROL, "min-h-[5rem] py-2", error && "border-red-400", className)}
                  aria-invalid={error ? true : undefined} {...rest} />
      </FieldWrapper>
    );
  },
);
Textarea.displayName = "Textarea";
