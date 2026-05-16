import { redirect } from "next/navigation";

export default function Page({ params }: { params: { id: string } }) {
  redirect(`/dashboard/finance?tab=fixed-assets&id=${encodeURIComponent(params.id)}&drawer=add-component`);
}
