import { Product } from "../types";
import { CATALOG_PRODUCTS } from "../data/products";
import { Shirt, Headphones, Backpack, Coffee, Watch, PlusCircle, Check } from "lucide-react";

interface ProductCatalogProps {
  selectedProduct: Product | null;
  isCustomProduct: boolean;
  onSelectProduct: (prod: Product) => void;
  onSelectCustom: () => void;
}

export function ProductCatalog({
  selectedProduct,
  isCustomProduct,
  onSelectProduct,
  onSelectCustom
}: ProductCatalogProps) {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case "Shirt":
        return <Shirt className="w-5 h-5" />;
      case "Headphones":
        return <Headphones className="w-5 h-5" />;
      case "Backpack":
        return <Backpack className="w-5 h-5" />;
      case "Coffee":
        return <Coffee className="w-5 h-5" />;
      case "Watch":
        return <Watch className="w-5 h-5" />;
      default:
        return <Shirt className="w-5 h-5" />;
    }
  };

  return (
    <div id="product-catalog-section" className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Featured Products
        </label>
        <button
          type="button"
          id="btn-select-custom-product"
          onClick={onSelectCustom}
          className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg border transition-all ${
            isCustomProduct
              ? "bg-blue-600 text-white border-blue-600 shadow-xs"
              : "bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200"
          }`}
        >
          <PlusCircle className="w-3.5 h-3.5" />
          Custom Item
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        {CATALOG_PRODUCTS.map((prod) => {
          const isSelected = !isCustomProduct && selectedProduct?.id === prod.id;
          return (
            <button
              key={prod.id}
              type="button"
              id={`product-card-${prod.id}`}
              onClick={() => onSelectProduct(prod)}
              className={`text-left p-3 rounded-xl border transition-all flex flex-col justify-between relative group ${
                isSelected
                  ? "bg-blue-50/90 border-blue-600 text-blue-950 ring-1 ring-blue-600 shadow-xs"
                  : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50 text-slate-800"
              }`}
            >
              {prod.badge && (
                <span className="absolute top-2 right-2 text-[10px] font-semibold tracking-wide uppercase px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                  {prod.badge}
                </span>
              )}

              <div className="flex items-center gap-2 mb-2">
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                    isSelected
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-600 group-hover:bg-slate-200"
                  }`}
                >
                  {getIcon(prod.icon)}
                </div>
                {isSelected && (
                  <span className="ml-auto w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center">
                    <Check className="w-3 h-3" />
                  </span>
                )}
              </div>

              <div>
                <h4 className="font-semibold text-xs leading-snug line-clamp-2">
                  {prod.name}
                </h4>
                <p className="text-xs font-bold text-slate-900 mt-1">
                  ${prod.price.toFixed(2)}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
