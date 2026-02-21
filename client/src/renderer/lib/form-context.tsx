import { createContext, useContext, useState, useCallback } from "react";
import type { ReactNode } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FormContextState {
  formCode: string;
  section: string;
  setFormContext: (formCode: string, section: string) => void;
  clearFormContext: () => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const FormContext = createContext<FormContextState>({
  formCode: "",
  section: "",
  setFormContext: () => {},
  clearFormContext: () => {},
});

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function FormContextProvider({ children }: { children: ReactNode }) {
  const [formCode, setFormCode] = useState("");
  const [section, setSection] = useState("");

  const setFormContext = useCallback((code: string, sec: string) => {
    setFormCode(code);
    setSection(sec);
  }, []);

  const clearFormContext = useCallback(() => {
    setFormCode("");
    setSection("");
  }, []);

  return (
    <FormContext.Provider value={{ formCode, section, setFormContext, clearFormContext }}>
      {children}
    </FormContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useFormContext() {
  return useContext(FormContext);
}
