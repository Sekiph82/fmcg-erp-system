import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/hr?tab=recruitment&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
