import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/marketing?tab=overview&id=${encodeURIComponent(params.id)}`);
}
