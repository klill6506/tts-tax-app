import { useCallback } from "react";

/**
 * Expand 2-digit years in a date value (YYYY-MM-DD format from type="date").
 * Pivot: 00-30 → 2000-2030, 31-99 → 1931-1999.
 */
function normalizeDateYear(value: string): string {
  if (!value) return value;
  const match = value.match(/^(\d{1,4})-(\d{2})-(\d{2})$/);
  if (!match) return value;
  let year = parseInt(match[1], 10);
  if (year >= 0 && year < 100) {
    year = year <= 30 ? 2000 + year : 1900 + year;
  }
  return `${year}-${match[2]}-${match[3]}`;
}

interface DateInputProps {
  value?: string;
  defaultValue?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onBlur?: (e: React.FocusEvent<HTMLInputElement>) => void;
  className?: string;
  disabled?: boolean;
}

/**
 * Date input that auto-expands 2-digit years on blur.
 * Drop-in replacement for <input type="date" />.
 */
export default function DateInput({
  value,
  defaultValue,
  onChange,
  onBlur,
  className,
  disabled,
}: DateInputProps) {
  const handleBlur = useCallback(
    (e: React.FocusEvent<HTMLInputElement>) => {
      const raw = e.target.value;
      const normalized = normalizeDateYear(raw);
      if (normalized !== raw) {
        // Update the DOM element directly so the normalized value shows
        e.target.value = normalized;
        // Fire onChange if this is a controlled input
        if (onChange) {
          const syntheticEvent = Object.create(e, {
            target: { value: { ...e.target, value: normalized } },
          });
          onChange(syntheticEvent);
        }
      }
      onBlur?.(e);
    },
    [onChange, onBlur],
  );

  return (
    <input
      type="date"
      value={value}
      defaultValue={defaultValue}
      onChange={onChange}
      onBlur={handleBlur}
      className={className}
      disabled={disabled}
    />
  );
}
