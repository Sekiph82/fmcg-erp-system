import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/admin?tab=custom-fields&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
