import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/inventory?tab=traceability&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
