import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/production?tab=projects&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
