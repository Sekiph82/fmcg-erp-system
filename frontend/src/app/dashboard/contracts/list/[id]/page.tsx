import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/sales?tab=contracts&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
