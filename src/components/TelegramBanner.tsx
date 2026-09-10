import { useEffect, useState } from "react";
import { Send, CheckCircle2, Globe, ShieldCheck, Sparkles, ExternalLink, Bot } from "lucide-react";
import { TelegramUser } from "../types";

interface TelegramBannerProps {
  isInsideTelegram: boolean;
  tgUser: TelegramUser | null;
  platform: string;
  onOpenBotGuide: () => void;
}

export function TelegramBanner({
  isInsideTelegram,
  tgUser,
  platform,
  onOpenBotGuide
}: TelegramBannerProps) {
  return (
    <div
      id="telegram-environment-banner"
      className={`rounded-2xl border p-4 transition-all duration-300 ${
        isInsideTelegram
          ? "bg-blue-50/80 border-blue-200/90 text-blue-950 shadow-xs"
          : "bg-white border-slate-200/90 text-slate-800 shadow-xs"
      }`}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              isInsideTelegram
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-700"
            }`}
          >
            {isInsideTelegram ? (
              <Send className="w-5 h-5 -rotate-12 translate-x-px" />
            ) : (
              <Globe className="w-5 h-5" />
            )}
          </div>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-sm">
                {isInsideTelegram
                  ? "Telegram Mini App Active"
                  : "Standard Web Browser Mode"}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  isInsideTelegram
                    ? "bg-blue-100 text-blue-800"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                {platform ? platform.toUpperCase() : "WEB"}
              </span>
              {isInsideTelegram && (
                <span className="inline-flex items-center gap-1 text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full font-medium border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3" /> Auto-Sync On
                </span>
              )}
            </div>

            <p className="text-xs text-slate-600 mt-0.5">
              {isInsideTelegram ? (
                <>
                  Logged in as{" "}
                  <strong className="text-slate-900">
                    {tgUser?.first_name} {tgUser?.last_name || ""}
                  </strong>
                  {tgUser?.username && ` (@${tgUser.username})`} • SDK Ready
                </>
              ) : (
                "Running in web browser. Orders can be submitted normally and alerts are routed to Telegram."
              )}
            </p>
          </div>
        </div>

        <button
          type="button"
          id="btn-telegram-bot-config"
          onClick={onOpenBotGuide}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg border border-blue-200/80 transition-colors"
        >
          <Bot className="w-3.5 h-3.5" />
          Bot & Alert Setup
        </button>
      </div>
    </div>
  );
}
