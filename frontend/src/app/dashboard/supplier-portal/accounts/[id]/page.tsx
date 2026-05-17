import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/procurement?tab=supplier-portal&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
