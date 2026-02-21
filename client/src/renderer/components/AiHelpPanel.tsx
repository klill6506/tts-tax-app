import { useState, useRef, useEffect } from "react";
import { post } from "../lib/api";
import { useFormContext } from "../lib/form-context";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Mode = "grounded" | "broad";

interface Message {
  role: "user" | "assistant";
  text: string;
  mode?: Mode;
}

// ---------------------------------------------------------------------------
// AI Help Panel — floating button + slide-out chat
// ---------------------------------------------------------------------------

export default function AiHelpPanel() {
  const { formCode, section } = useFormContext();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<Mode>("grounded");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 100);
  }, [isOpen]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setInput("");
    setLoading(true);

    try {
      const res = await post("/ai/ask/", {
        question: q,
        form_code: formCode || "",
        section: section || "",
        mode,
      });
      if (res.ok) {
        const data = res.data as { answer: string; mode: Mode };
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: data.answer, mode: data.mode },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Sorry, something went wrong. Please try again." },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Unable to reach the server." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {/* Panel */}
      {isOpen && (
        <div className="fixed bottom-16 right-4 z-[80] flex w-96 flex-col rounded-xl border border-border bg-card shadow-2xl"
          style={{ height: "500px", maxHeight: "calc(100vh - 120px)" }}
        >
          {/* Header */}
          <div className="shrink-0 border-b border-border px-4 py-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-tx">AI Tax Help</h3>
              <button
                onClick={() => setIsOpen(false)}
                className="rounded-md p-1 text-tx-muted transition hover:bg-surface hover:text-tx"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Context line */}
            {formCode ? (
              <p className="mt-0.5 text-xs text-tx-muted">
                Context: Form {formCode}
                {section ? ` — ${section}` : ""}
              </p>
            ) : (
              <p className="mt-0.5 text-xs text-tx-muted">General tax guidance</p>
            )}

            {/* Mode toggle */}
            <div className="mt-2 flex gap-1">
              <button
                onClick={() => setMode("grounded")}
                className={`rounded-full px-2.5 py-1 text-xs font-medium transition ${
                  mode === "grounded"
                    ? "bg-primary text-white"
                    : "bg-surface text-tx-muted hover:text-tx"
                }`}
              >
                IRS Instructions
              </button>
              <button
                onClick={() => setMode("broad")}
                className={`rounded-full px-2.5 py-1 text-xs font-medium transition ${
                  mode === "broad"
                    ? "bg-primary text-white"
                    : "bg-surface text-tx-muted hover:text-tx"
                }`}
              >
                Broader Search
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-auto px-4 py-3 space-y-3">
            {messages.length === 0 && (
              <div className="mt-8 text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary-subtle">
                  <svg className="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-tx">Ask me about tax preparation</p>
                <p className="mt-1 text-xs text-tx-muted">
                  Use <strong>IRS Instructions</strong> for answers grounded in official
                  IRS guidance, or <strong>Broader Search</strong> for general tax topics.
                </p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === "user"
                      ? "bg-primary text-white"
                      : "bg-surface text-tx"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  {msg.role === "assistant" && msg.mode && (
                    <span className="mt-1 block text-[10px] opacity-60">
                      {msg.mode === "grounded"
                        ? "Source: IRS Instructions"
                        : "Source: General Knowledge"}
                    </span>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="rounded-lg bg-surface px-3 py-2 text-sm text-tx-muted">
                  <span className="inline-flex gap-1">
                    <span className="animate-pulse">Thinking</span>
                    <span className="animate-bounce" style={{ animationDelay: "0.1s" }}>.</span>
                    <span className="animate-bounce" style={{ animationDelay: "0.2s" }}>.</span>
                    <span className="animate-bounce" style={{ animationDelay: "0.3s" }}>.</span>
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="shrink-0 border-t border-border px-3 py-2">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a tax question..."
                disabled={loading}
                className="flex-1 rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx outline-none focus:ring-2 focus:ring-focus-ring disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white transition hover:bg-primary-hover disabled:opacity-50"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Floating button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-4 right-4 z-[80] flex h-12 w-12 items-center justify-center rounded-full shadow-lg transition hover:shadow-xl ${
          isOpen
            ? "bg-tx text-white"
            : "bg-primary text-white hover:bg-primary-hover"
        }`}
        title="AI Tax Help"
      >
        {isOpen ? (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        ) : (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
          </svg>
        )}
      </button>
    </>
  );
}
