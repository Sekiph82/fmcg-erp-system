import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/documents?id=${encodeURIComponent(params.id)}&drawer=detail`);
}
