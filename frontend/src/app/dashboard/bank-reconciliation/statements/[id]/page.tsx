import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/finance?tab=bank-recon&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
