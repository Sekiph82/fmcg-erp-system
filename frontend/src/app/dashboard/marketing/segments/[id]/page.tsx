import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/marketing?tab=segments&id=${encodeURIComponent(params.id)}&drawer=detail`);
}
