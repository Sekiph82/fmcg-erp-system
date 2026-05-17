import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/logistics?tab=containers");
}
