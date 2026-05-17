import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/procurement?tab=purchase-requests&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
