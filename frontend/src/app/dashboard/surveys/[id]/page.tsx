import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/crm?tab=surveys&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
