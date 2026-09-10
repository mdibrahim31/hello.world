import { useState } from "react";
import { Order } from "../types";
import { CheckCircle2, Copy, Check, Send, AlertCircle, ShoppingCart, X, MessageSquare } from "lucide-react";

interface OrderSuccessModalProps {
  order: Order;
  telegramResult?: any;
  telegramPreview?: string;
  isInsideTelegram: boolean;
  onClose: () => void;
}

export function OrderSuccessModal({
  order,
  telegramResult,
  telegramPreview,
  isInsideTelegram,
  onClose
}: OrderSuccessModalProps) {
  const [copied, setCopied] = useState(false);
  const [copiedOrderId, setCopiedOrderId] = useState(false);

  const isAlertSent = telegramResult?.success === true;
  const isSimulated = telegramResult?.isSimulated || telegramResult?.simulated;
  const previewText = telegramPreview || telegramResult?.preview_message || "";

  const handleCopyAlert = () => {
    if (!previewText) return;
    navigator.clipboard.writeText(previewText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyOrderId = () => {
    navigator.clipboard.writeText(order.order_number);
    setCopiedOrderId(true);
    setTimeout(() => setCopiedOrderId(false), 2000);
  };

  const handleCloseTelegram = () => {
    if (typeof window !== "undefined" && window.Telegram?.WebApp) {
      window.Telegram.WebApp.close();
    } else {
      onClose();
    }
  };

  return (
    <div
      id="order-success-modal-overlay"
      className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
    >
      <div
        id="order-success-card"
        className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95 duration-200 my-8"
      >
        {/* Header with success badge */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-7 h-7" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-slate-900">
                Order Placed Successfully!
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Saved in SQLite Database & Telegram Alert Triggered
              </p>
            </div>
          </div>
          <button
            type="button"
            id="btn-close-success-modal"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Order Details Receipt Box */}
        <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/80 space-y-2.5 text-xs">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <span className="text-slate-500 font-medium">Order Reference</span>
            <button
              type="button"
              id="btn-copy-order-id"
              onClick={handleCopyOrderId}
              className="inline-flex items-center gap-1 font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-300 hover:bg-slate-100"
            >
              {order.order_number}
              {copiedOrderId ? (
                <Check className="w-3 h-3 text-emerald-600" />
              ) : (
                <Copy className="w-3 h-3 text-slate-400" />
              )}
            </button>
          </div>

          <div className="flex justify-between">
            <span className="text-slate-500">Customer Name:</span>
            <span className="font-semibold text-slate-800">{order.customer_name}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-slate-500">Phone Number:</span>
            <span className="font-semibold text-slate-800">{order.phone_number}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-slate-500">Item & Qty:</span>
            <span className="font-semibold text-slate-800 text-right">
              {order.product_name} × {order.quantity}
            </span>
          </div>

          <div className="flex justify-between border-t border-slate-200 pt-2 font-bold text-sm">
            <span className="text-slate-900">Total Amount:</span>
            <span className="text-blue-600">${Number(order.total_price || 0).toFixed(2)}</span>
          </div>
        </div>

        {/* Telegram Alert Status Notice */}
        <div
          id="telegram-alert-status-box"
          className={`rounded-xl p-3.5 border text-xs space-y-2 ${
            isAlertSent
              ? "bg-emerald-50 border-emerald-200 text-emerald-950"
              : "bg-blue-50/70 border-blue-200 text-blue-950"
          }`}
        >
          <div className="flex items-center gap-2 font-semibold">
            <Send className="w-4 h-4 text-blue-600" />
            <span>
              {isAlertSent
                ? "Telegram Bot Alert Dispatched!"
                : isSimulated
                ? "Telegram Alert Formatted (Demo / Simulation)"
                : "Telegram Bot Alert Triggered"}
            </span>
          </div>
          <p className="text-[11px] text-slate-600 leading-relaxed">
            {isAlertSent
              ? `Real-time message delivered to your configured Telegram Chat ID.`
              : `The Python backend formatted the Telegram notification below. To receive alerts on your own Telegram chat/channel, add your BOT_TOKEN and CHAT_ID in Bot Setup.`}
          </p>

          {previewText && (
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-500">
                  Telegram Markdown Payload
                </span>
                <button
                  type="button"
                  id="btn-copy-telegram-alert"
                  onClick={handleCopyAlert}
                  className="inline-flex items-center gap-1 text-[11px] text-blue-600 font-medium hover:underline cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-600" /> Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" /> Copy Text
                    </>
                  )}
                </button>
              </div>
              <pre className="bg-slate-900 text-slate-100 font-mono text-[11px] p-2.5 rounded-lg overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-36">
                {previewText}
              </pre>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-2 pt-1">
          <button
            type="button"
            id="btn-place-another"
            onClick={onClose}
            className="flex-1 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <ShoppingCart className="w-4 h-4" />
            Place Another Order
          </button>

          {isInsideTelegram && (
            <button
              type="button"
              id="btn-close-telegram-app"
              onClick={handleCloseTelegram}
              className="py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-xs rounded-xl transition-colors cursor-pointer"
            >
              Close Mini App
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
