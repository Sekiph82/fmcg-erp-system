"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { aiApi, AIChatResponse } from "@/lib/aiApi";
import { Button } from "@/components/ui/Button";

interface Message {
  role: "user" | "assistant";
  content: string;
  meta?: { provider?: string; mode?: string; latency_ms?: number };
}

const EXAMPLE_QUESTIONS = [
  "What is the current inventory status?",
  "How are sales trending over the last 90 days?",
  "Which products are at reorder risk?",
  "What is our outstanding receivables balance?",
  "How many open purchase orders do we have?",
];

export default function ERPChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: status } = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiApi.status(),
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text?: string) {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    const userMsg: Message = { role: "user", content: msg };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    setError("");

    try {
      const history = newMessages
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));

      const res: AIChatResponse = await aiApi.chat(msg, history);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          meta: { provider: res.provider, mode: res.mode, latency_ms: res.latency_ms },
        },
      ]);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail || "Chat request failed. Check backend logs.");
    }
    setLoading(false);
  }

  const isMock = status?.mode === "mock" || !status?.configured;

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">ERP Copilot</h1>
          <p className="text-xs text-gray-500 mt-0.5">Ask anything about sales, inventory, procurement, or finance</p>
        </div>
        <div className="flex items-center gap-2">
          {isMock ? (
            <span className="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded-full font-medium">
              DEV/MOCK MODE — No real AI key
            </span>
          ) : (
            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full font-medium">
              LIVE — {status?.provider} / {status?.model}
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <div className="text-4xl mb-3">💬</div>
            <p className="text-gray-500 text-sm mb-6">Ask any question about your ERP data</p>
            <div className="grid grid-cols-1 gap-2 max-w-md mx-auto">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="text-left text-sm bg-white border border-gray-200 rounded-xl px-4 py-2.5 hover:border-indigo-300 hover:bg-indigo-50 transition-colors text-gray-700"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] ${m.role === "user" ? "order-2" : "order-1"}`}>
              <div
                className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-white border border-gray-200 text-gray-800"
                }`}
              >
                {m.content}
              </div>
              {m.meta && (
                <div className="mt-1 flex gap-2 text-xs text-gray-400 px-1">
                  {m.meta.mode === "mock" && (
                    <span className="text-amber-500">Mock mode</span>
                  )}
                  {m.meta.provider && <span>{m.meta.provider}</span>}
                  {m.meta.latency_ms && <span>{m.meta.latency_ms}ms</span>}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-white border border-gray-200 rounded-2xl p-3 flex gap-3 items-end shadow-sm">
        <textarea
          className="flex-1 text-sm resize-none outline-none text-gray-800 placeholder-gray-400 max-h-32"
          placeholder="Ask about sales, inventory, orders, suppliers..."
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          disabled={loading}
        />
        <Button onClick={() => sendMessage()} loading={loading} className="shrink-0">
          Send
        </Button>
      </div>
      <p className="text-xs text-gray-400 text-center mt-2">
        Press Enter to send · Shift+Enter for new line · ERP data is live from DB
        {isMock && " · Running in mock mode — no API key configured"}
      </p>
    </div>
  );
}
