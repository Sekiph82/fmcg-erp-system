import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/crm?tab=overview&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
