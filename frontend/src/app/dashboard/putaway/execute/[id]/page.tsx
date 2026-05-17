import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/warehouses?tab=wms&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
