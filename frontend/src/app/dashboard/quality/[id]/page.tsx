import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/quality?tab=qms&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
