import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/crm?tab=surveys&drawer=create");
}
