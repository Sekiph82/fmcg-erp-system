import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/production?tab=orders&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
