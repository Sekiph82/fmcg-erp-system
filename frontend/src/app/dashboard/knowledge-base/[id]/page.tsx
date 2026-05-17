import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/documents?tab=knowledge-base&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
