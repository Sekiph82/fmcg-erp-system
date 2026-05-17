import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/admin?tab=roles&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
