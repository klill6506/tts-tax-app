import { useState, useEffect, useRef } from "react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(raw: string): string {
  if (!raw || raw === "" || raw === "-") return "";
  const num = parseFloat(raw);
  if (isNaN(num) || num === 0) return "";
  const abs = Math.abs(num);
  const formatted = abs.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (num < 0) return `($${formatted})`;
  return `$${formatted}`;
}

function parseCurrency(input: string): string {
  if (!input || input.trim() === "") return "";
  let cleaned = input.replace(/[$,\s]/g, "");
  // Accounting-style negatives: (123.45) → -123.45
  if (cleaned.startsWith("(") && cleaned.endsWith(")")) {
    cleaned = "-" + cleaned.slice(1, -1);
  }
  const num = parseFloat(cleaned);
  if (isNaN(num)) return "";
  return num.toString();
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
      inputMode="decimal"
      value={displayValue}
      readOnly={readOnly}
      onChange={(e) => setDisplayValue(e.target.value)}
      onFocus={handleFocus}
      onBlur={handleBlur}
      className={`w-full rounded-md border border-input-border px-2 py-1 text-right text-sm tabular-nums shadow-sm
        placeholder:text-tx-muted
        focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring
        ${readOnly ? "bg-surface-alt text-tx-secondary cursor-default" : "bg-input text-tx"}
        ${className || ""}`}
    />
  );
}
