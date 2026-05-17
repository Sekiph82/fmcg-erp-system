import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/documents?tab=knowledge-base");
}
