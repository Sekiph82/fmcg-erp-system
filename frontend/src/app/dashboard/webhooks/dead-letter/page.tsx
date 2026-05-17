import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/integrations?tab=webhooks");
}
