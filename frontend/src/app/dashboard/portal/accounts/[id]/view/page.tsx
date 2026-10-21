import { redirect } from "next/navigation";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/dashboard/sales?tab=portal&id=${encodeURIComponent(id)}&drawer=detail`);
}
