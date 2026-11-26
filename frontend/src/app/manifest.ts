import type { MetadataRoute } from "next";

// Installable employee app (M37). Distribution decision: coordination/milestones/M37/M37_MOBILE_APP_DISTRIBUTION_DECISION.md
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "POVU ERP",
    short_name: "POVU",
    description: "POVU factory ERP for employees",
    start_url: "/dashboard?source=pwa",
    scope: "/",
    display: "standalone",
    orientation: "any",
    background_color: "#f9fafb",
    theme_color: "#4338ca",
    icons: [
      { src: "/icons/povu-icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/povu-icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
    ],
    shortcuts: [
      { name: "Shop Floor Terminal", url: "/dashboard/shop-floor/terminal" },
      { name: "Approvals", url: "/dashboard/mobile/approvals" },
      { name: "Field app", url: "/dashboard/field" },
      { name: "Warehouse floor", url: "/dashboard/warehouse-floor" },
    ],
  };
}
