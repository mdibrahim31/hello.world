import React, { useState, useEffect, type FormEvent } from "react";
import { Bot, Send, CheckCircle2, Copy, Check, FileCode, X } from "lucide-react";
import { BotConfig } from "../types";
import { CODE_SNIPPETS } from "../data/codeSnippets";

interface BotIntegrationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function BotIntegrationModal({ isOpen, onClose }: BotIntegrationModalProps) {
  const [config, setConfig] = useState<BotConfig | null>(null);
  const [botToken, setBotToken] = useState("");
  const [chatId, setChatId] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [activeCodeTab, setActiveCodeTab] = useState<"app.py" | "database.py" | "bot.py" | "requirements.txt" | "render.yaml">("app.py");
  const [copiedTab, setCopiedTab] = useState(false);

  // Fetch current config on open
  const fetchConfig = async () => {
    try {
      const res = await fetch("/api/config");
      const data = await res.json();
      setConfig(data);
      if (data.chat_id) {
        setChatId(data.chat_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchConfig();
      setTestResult(null);
    }
  }, [isOpen]);

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bot_token: botToken, chat_id: chatId })
      });
      const data = await res.json();
      if (data.success) {
        await fetchConfig();
        setTestResult({ success: true, message: "Configuration saved successfully!" });
      }
    } catch (err: any) {
      setTestResult({ success: false, error: err.message });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestPing = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await fetch("/api/test-telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bot_token: botToken || undefined, chat_id: chatId || undefined })
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err: any) {
      setTestResult({ success: false, error: err.message });
    } finally {
      setIsTesting(false);
    }
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(CODE_SNIPPETS[activeCodeTab] || "");
    setCopiedTab(true);
    setTimeout(() => setCopiedTab(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <div
      id="bot-integration-modal-overlay"
      className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
    >
      <div
        id="bot-integration-dialog"
        className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95 duration-200 my-8 max-h-[92vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                Telegram Bot & Alert Integration
              </h3>
              <p className="text-xs text-slate-500">
                Configure real-time alerts, test Telegram webhook, and export Python files
              </p>
            </div>
          </div>
          <button
            type="button"
            id="btn-close-bot-modal"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Setup Steps Guide */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-5 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center mb-1.5">
                1
              </span>
              <h4 className="font-bold text-slate-800">Create Bot</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                Open Telegram, talk to <strong>@BotFather</strong>, send <code className="bg-white px-1 py-0.5 rounded border border-slate-200">/newbot</code> to get your Bot Token.
              </p>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center mb-1.5">
                2
              </span>
              <h4 className="font-bold text-slate-800">Get Chat ID</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                Add bot to your channel or group as Admin, or send <code className="bg-white px-1 py-0.5 rounded border border-slate-200">/status</code> to your bot to view your ID.
              </p>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center mb-1.5">
                3
              </span>
              <h4 className="font-bold text-slate-800">Launch Mini App</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                Run <code className="bg-white px-1 py-0.5 rounded border border-slate-200">python bot.py</code>. Bot replies to <code className="bg-white px-1 py-0.5 rounded border border-slate-200">/start</code> with Mini App button.
              </p>
            </div>
          </div>

          {/* Bot Configuration Form */}
          <form onSubmit={handleSaveConfig} className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-3">
            <h4 className="font-bold text-slate-800 flex items-center justify-between">
              <span>Live Telegram Credentials</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                config?.has_bot_token && config?.has_chat_id
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-amber-100 text-amber-800"
              }`}>
                {config?.has_bot_token && config?.has_chat_id ? "Active" : "Not Configured / Demo Mode"}
              </span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-600 font-medium mb-1">
                  Telegram Bot Token
                </label>
                <input
                  type="password"
                  value={botToken}
                  onChange={(e) => setBotToken(e.target.value)}
                  placeholder={config?.bot_token_masked || "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"}
                  className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-mono text-[11px]"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-medium mb-1">
                  Chat / Channel ID
                </label>
                <input
                  type="text"
                  value={chatId}
                  onChange={(e) => setChatId(e.target.value)}
                  placeholder="-1001234567890 or 987654321"
                  className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-mono text-[11px]"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <button
                type="submit"
                disabled={isSaving || (!botToken && !chatId)}
                className="py-1.5 px-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-lg transition-colors cursor-pointer"
              >
                {isSaving ? "Saving..." : "Save Credentials"}
              </button>

              <button
                type="button"
                id="btn-test-telegram-alert"
                onClick={handleTestPing}
                disabled={isTesting}
                className="py-1.5 px-3 bg-slate-200 hover:bg-slate-300 text-slate-800 font-medium rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Send className={`w-3.5 h-3.5 ${isTesting ? "animate-pulse" : ""}`} />
                {isTesting ? "Sending Ping..." : "Send Test Alert Ping"}
              </button>
            </div>

            {testResult && (
              <div
                className={`p-3 rounded-lg border text-xs leading-relaxed ${
                  testResult.success
                    ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                    : "bg-rose-50 border-rose-200 text-rose-800"
                }`}
              >
                {testResult.success ? (
                  <div className="flex items-center gap-1.5 font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Telegram Test Message Dispatched Successfully!
                  </div>
                ) : (
                  <div>
                    <strong>Verification Feedback:</strong> {testResult.error || "Simulation mode active"}
                    {testResult.previewMessage && (
                      <p className="mt-1 text-[11px] opacity-80">
                        A test notification markdown payload was generated and verified.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </form>

          {/* Python Files Deployment Preview */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-slate-800 flex items-center gap-1.5">
                <FileCode className="w-4 h-4 text-blue-600" />
                Generated Python Deployment Files
              </h4>
              <button
                type="button"
                onClick={handleCopyCode}
                className="inline-flex items-center gap-1 text-blue-600 hover:underline font-medium cursor-pointer"
              >
                {copiedTab ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" /> Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" /> Copy Code
                  </>
                )}
              </button>
            </div>

            {/* Tab navigation */}
            <div className="flex border-b border-slate-200 gap-1 overflow-x-auto">
              {(["app.py", "database.py", "bot.py", "requirements.txt", "render.yaml"] as const).map(
                (tab) => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setActiveCodeTab(tab)}
                    className={`px-3 py-1.5 font-mono text-xs font-medium border-b-2 transition-colors cursor-pointer shrink-0 ${
                      activeCodeTab === tab
                        ? "border-blue-600 text-blue-600"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    {tab}
                  </button>
                )
              )}
            </div>

            <pre className="bg-slate-900 text-slate-200 font-mono text-[11px] p-3.5 rounded-xl overflow-x-auto max-h-48 leading-relaxed">
              {CODE_SNIPPETS[activeCodeTab]}
            </pre>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="border-t border-slate-100 pt-3 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-xs rounded-xl transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
