import { useState, useEffect, useRef } from "react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(raw: string): string {
  if (!raw || raw === "" || raw === "-") return "";
  const num = parseFloat(raw);
  if (isNaN(num) || num === 0) return "";
  const rounded = Math.round(num);
  const abs = Math.abs(rounded);
  const formatted = abs.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
  if (rounded < 0) return `(${formatted})`;
  return formatted;
}

function parseCurrency(input: string): string {
  if (!input || input.trim() === "") return "";
  let cleaned = input.replace(/[$,\s]/g, "");
  // Accounting-style negatives: (123) → -123
  if (cleaned.startsWith("(") && cleaned.endsWith(")")) {
    cleaned = "-" + cleaned.slice(1, -1);
  }
  const num = parseFloat(cleaned);
  if (isNaN(num)) return "";
  // Whole dollars only — round to nearest integer
  return Math.round(num).toString();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface CurrencyInputProps {
  value: string;
  onValueChange: (raw: string) => void;
  readOnly?: boolean;
  className?: string;
}

export default function CurrencyInput({
  value,
  onValueChange,
  readOnly,
  className,
}: CurrencyInputProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [displayValue, setDisplayValue] = useState(formatCurrency(value));
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync display when value prop changes externally
  useEffect(() => {
    if (!isFocused) {
      setDisplayValue(formatCurrency(value));
    }
  }, [value, isFocused]);

  function handleFocus() {
    if (readOnly) return;
    setIsFocused(true);
    setDisplayValue(value || "");
    setTimeout(() => inputRef.current?.select(), 0);
  }

  function handleBlur() {
    const parsed = parseCurrency(displayValue);
    setIsFocused(false);
    setDisplayValue(formatCurrency(parsed));
    if (parsed !== value) {
      onValueChange(parsed);
    }
  }

  return (
    <input
      ref={inputRef}
      type="text"
      inputMode="numeric"
      value={displayValue}
      readOnly={readOnly}
      onChange={(e) => setDisplayValue(e.target.value)}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onKeyDown={(e) => {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          e.preventDefault();
          const inputs = Array.from(
            document.querySelectorAll<HTMLInputElement>(
              'input[type="text"]:not([readonly])',
            ),
          );
          const idx = inputs.indexOf(e.currentTarget);
          if (idx < 0) return;
          const next = e.key === "ArrowDown" ? idx + 1 : idx - 1;
          if (next >= 0 && next < inputs.length) {
            inputs[next].focus();
          }
        }
      }}
      className={`w-full rounded-md border border-input-border px-2 py-1 text-right text-sm tabular-nums shadow-sm
        placeholder:text-tx-muted
        focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring
        ${readOnly ? "bg-surface-alt text-tx-secondary cursor-default" : "bg-input text-tx"}
        ${className || ""}`}
    />
  );
}
