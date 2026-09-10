import React, { useState, useEffect } from "react";
import { Product, TelegramUser } from "../types";
import { User, Phone, Package, Hash, FileText, ShoppingBag, Loader2, Sparkles, CheckCircle } from "lucide-react";
import { ProductCatalog } from "./ProductCatalog";
import { CATALOG_PRODUCTS } from "../data/products";

interface OrderFormProps {
  isInsideTelegram: boolean;
  tgUser: TelegramUser | null;
  onSubmitOrder: (formData: {
    customer_name: string;
    phone_number: string;
    product_name: string;
    quantity: number;
    unit_price: number;
    total_price: number;
    notes: string;
  }) => Promise<void>;
  isSubmitting: boolean;
}

export function OrderForm({
  isInsideTelegram,
  tgUser,
  onSubmitOrder,
  isSubmitting
}: OrderFormProps) {
  // Form State
  const [customerName, setCustomerName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(CATALOG_PRODUCTS[0]);
  const [customProductName, setCustomProductName] = useState("");
  const [customUnitPrice, setCustomUnitPrice] = useState("25.00");
  const [isCustomProduct, setIsCustomProduct] = useState(false);
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState("");
  const [validationErrors, setValidationErrors] = useState<{ [key: string]: string }>({});

  // Auto-fill customer name from Telegram if available
  useEffect(() => {
    if (tgUser) {
      const fullName = [tgUser.first_name, tgUser.last_name].filter(Boolean).join(" ");
      if (fullName && !customerName) {
        setCustomerName(fullName);
      }
    }
  }, [tgUser]);

  // Determine current active product name and unit price
  const activeProductName = isCustomProduct ? customProductName : (selectedProduct?.name || "");
  const activeUnitPrice = isCustomProduct
    ? (parseFloat(customUnitPrice) || 0)
    : (selectedProduct?.price || 0);
  const totalPrice = activeUnitPrice * quantity;

  // Setup Telegram MainButton if inside Telegram
  useEffect(() => {
    if (typeof window !== "undefined" && window.Telegram?.WebApp) {
      const webApp = window.Telegram.WebApp;
      const mainBtn = webApp.MainButton;

      if (mainBtn) {
        if (customerName.trim() && phoneNumber.trim() && activeProductName.trim()) {
          mainBtn.setText(`PLACE ORDER • $${totalPrice.toFixed(2)}`);
          mainBtn.enable();
          mainBtn.show();
        } else {
          mainBtn.setText(`COMPLETE DETAILS • $${totalPrice.toFixed(2)}`);
          mainBtn.disable();
          mainBtn.show();
        }

        const handleMainButtonClick = () => {
          handleFormSubmit();
        };

        mainBtn.onClick(handleMainButtonClick);
        return () => {
          mainBtn.offClick(handleMainButtonClick);
        };
      }
    }
  }, [customerName, phoneNumber, activeProductName, totalPrice]);

  const handleSelectProduct = (prod: Product) => {
    setIsCustomProduct(false);
    setSelectedProduct(prod);
    setValidationErrors((prev) => ({ ...prev, product_name: "" }));
  };

  const handleSelectCustom = () => {
    setIsCustomProduct(true);
    setSelectedProduct(null);
  };

  const handleFormSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    const errors: { [key: string]: string } = {};
    if (!customerName.trim()) {
      errors.customer_name = "Please enter customer name.";
    }
    if (!phoneNumber.trim()) {
      errors.phone_number = "Please enter a valid contact phone number.";
    } else if (phoneNumber.trim().length < 6) {
      errors.phone_number = "Phone number is too short.";
    }
    if (!activeProductName.trim()) {
      errors.product_name = "Please select or specify a product name.";
    }
    if (quantity < 1) {
      errors.quantity = "Quantity must be at least 1.";
    }

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      if (typeof window !== "undefined" && window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred("error");
      }
      return;
    }

    setValidationErrors({});
    await onSubmitOrder({
      customer_name: customerName.trim(),
      phone_number: phoneNumber.trim(),
      product_name: activeProductName.trim(),
      quantity: quantity,
      unit_price: activeUnitPrice,
      total_price: totalPrice,
      notes: notes.trim()
    });
  };

  return (
    <form
      id="order-submission-form"
      onSubmit={handleFormSubmit}
      className="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-5 sm:p-6 space-y-6"
    >
      <div className="border-b border-slate-100 pb-4">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <ShoppingBag className="w-5 h-5 text-blue-600" />
          Create New Order
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Complete the details below. Once placed, an automated Telegram alert will be dispatched instantly.
        </p>
      </div>

      {/* Product Selection Catalog */}
      <ProductCatalog
        selectedProduct={selectedProduct}
        isCustomProduct={isCustomProduct}
        onSelectProduct={handleSelectProduct}
        onSelectCustom={handleSelectCustom}
      />

      {/* Custom Product Input (if toggled) */}
      {isCustomProduct && (
        <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 space-y-3">
          <div>
            <label
              htmlFor="custom_product_name"
              className="block text-xs font-semibold text-slate-700 mb-1"
            >
              Custom Item Name *
            </label>
            <input
              id="custom_product_name"
              type="text"
              required
              value={customProductName}
              onChange={(e) => {
                setCustomProductName(e.target.value);
                setValidationErrors((prev) => ({ ...prev, product_name: "" }));
              }}
              placeholder="e.g., Customized Silk Scarf, Special Bundle"
              className="w-full text-sm px-3 py-2 bg-white rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
            />
          </div>
          <div className="w-40">
            <label
              htmlFor="custom_unit_price"
              className="block text-xs font-semibold text-slate-700 mb-1"
            >
              Unit Price ($)
            </label>
            <input
              id="custom_unit_price"
              type="number"
              step="0.01"
              min="0"
              value={customUnitPrice}
              onChange={(e) => setCustomUnitPrice(e.target.value)}
              className="w-full text-sm px-3 py-2 bg-white rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
            />
          </div>
        </div>
      )}

      {validationErrors.product_name && (
        <p className="text-xs text-rose-600 font-medium">
          {validationErrors.product_name}
        </p>
      )}

      {/* Customer Info Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Customer Name */}
        <div>
          <label
            htmlFor="customer_name"
            className="block text-xs font-semibold text-slate-700 mb-1.5"
          >
            Customer Full Name *
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <User className="w-4 h-4" />
            </div>
            <input
              id="customer_name"
              type="text"
              required
              value={customerName}
              onChange={(e) => {
                setCustomerName(e.target.value);
                setValidationErrors((prev) => ({ ...prev, customer_name: "" }));
              }}
              placeholder="e.g. John Doe"
              className={`w-full pl-9.5 pr-3 py-2.5 text-sm bg-white rounded-xl border ${
                validationErrors.customer_name
                  ? "border-rose-400 focus:ring-rose-500/20"
                  : "border-slate-300 focus:ring-blue-500/20 focus:border-blue-600"
              } focus:outline-none focus:ring-2 transition-colors`}
            />
          </div>
          {validationErrors.customer_name && (
            <p className="text-xs text-rose-600 mt-1 font-medium">
              {validationErrors.customer_name}
            </p>
          )}
          {tgUser?.first_name && customerName.includes(tgUser.first_name) && (
            <p className="text-[11px] text-blue-600 mt-1 flex items-center gap-1 font-medium">
              <Sparkles className="w-3 h-3" /> Auto-populated from Telegram profile
            </p>
          )}
        </div>

        {/* Phone Number */}
        <div>
          <label
            htmlFor="phone_number"
            className="block text-xs font-semibold text-slate-700 mb-1.5"
          >
            Contact Phone Number *
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Phone className="w-4 h-4" />
            </div>
            <input
              id="phone_number"
              type="tel"
              required
              value={phoneNumber}
              onChange={(e) => {
                setPhoneNumber(e.target.value);
                setValidationErrors((prev) => ({ ...prev, phone_number: "" }));
              }}
              placeholder="e.g. +1 (555) 019-2834 or 017xxxxxxxx"
              className={`w-full pl-9.5 pr-3 py-2.5 text-sm bg-white rounded-xl border ${
                validationErrors.phone_number
                  ? "border-rose-400 focus:ring-rose-500/20"
                  : "border-slate-300 focus:ring-blue-500/20 focus:border-blue-600"
              } focus:outline-none focus:ring-2 transition-colors`}
            />
          </div>
          {validationErrors.phone_number ? (
            <p className="text-xs text-rose-600 mt-1 font-medium">
              {validationErrors.phone_number}
            </p>
          ) : (
            <p className="text-[11px] text-slate-400 mt-1">
              Used for courier dispatch confirmation
            </p>
          )}
        </div>
      </div>

      {/* Quantity Stepper & Order Calculation */}
      <div className="bg-slate-50/80 p-4 rounded-xl border border-slate-200/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <label
            htmlFor="order_quantity_input"
            className="block text-xs font-semibold text-slate-700 mb-1"
          >
            Order Quantity
          </label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              id="btn-decrement-qty"
              onClick={() => setQuantity((q) => Math.max(1, q - 1))}
              disabled={quantity <= 1}
              className="w-8 h-8 rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed font-bold text-base flex items-center justify-center transition-colors"
            >
              -
            </button>
            <input
              id="order_quantity_input"
              type="number"
              min="1"
              max="99"
              value={quantity}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10);
                setQuantity(isNaN(val) || val < 1 ? 1 : val);
              }}
              className="w-14 text-center font-bold text-sm py-1.5 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
            />
            <button
              type="button"
              id="btn-increment-qty"
              onClick={() => setQuantity((q) => Math.min(99, q + 1))}
              className="w-8 h-8 rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 font-bold text-base flex items-center justify-center transition-colors"
            >
              +
            </button>
          </div>
        </div>

        {/* Pricing Summary */}
        <div className="sm:text-right w-full sm:w-auto">
          <div className="text-xs text-slate-500">
            {quantity} × ${activeUnitPrice.toFixed(2)}
          </div>
          <div className="text-xl font-bold text-slate-900">
            Total: ${totalPrice.toFixed(2)}
          </div>
          <div className="text-[11px] text-emerald-600 font-medium">
            ✓ Free Express Dispatch
          </div>
        </div>
      </div>

      {/* Delivery Notes / Special Instructions */}
      <div>
        <label
          htmlFor="order_notes"
          className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5"
        >
          <FileText className="w-3.5 h-3.5 text-slate-400" />
          Delivery Address & Notes (Optional)
        </label>
        <textarea
          id="order_notes"
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g., Apt 4B, leave parcel at reception. Ring bell twice."
          className="w-full px-3 py-2 text-sm bg-white rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors placeholder:text-slate-400"
        />
      </div>

      {/* Submit Action Button */}
      <div className="pt-2">
        <button
          type="submit"
          id="btn-place-order"
          disabled={isSubmitting}
          className="w-full py-3.5 px-6 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold rounded-xl shadow-sm hover:shadow-md transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing & Alerting Telegram...
            </>
          ) : (
            <>
              <ShoppingBag className="w-4 h-4" />
              Place Order • ${totalPrice.toFixed(2)}
            </>
          )}
        </button>
        <p className="text-center text-[11px] text-slate-400 mt-2">
          {isInsideTelegram
            ? "Inside Telegram: You can also use Telegram's bottom action button to confirm."
            : "Direct HTTP POST to Python Backend (/api/order) + SQLite persistent record."}
        </p>
      </div>
    </form>
  );
}
