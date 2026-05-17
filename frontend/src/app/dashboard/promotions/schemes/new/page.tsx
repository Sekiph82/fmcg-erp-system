import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/marketing?tab=promotions-schemes&drawer=create");
}
